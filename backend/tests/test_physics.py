"""Program properties and API compatibility; no empirical thresholds."""

import math
import time
import numpy as np
import pytest
from pydantic import ValidationError
from elusim.engine import Program, band_width, retention_state, simulate, volume
from elusim.efficiency import effective_plates, reduced_height
from elusim.hydraulics import (
    viscosity, water_viscosity, organic_viscosity, column_pressure_bar,
    batch_max_pressure, pressure_profile,
)
from elusim.optimizer import evaluate, candidate, nodes_for, optimize_map
from elusim.schemas import Simulation, OptimizeMap
from test_engine import method


def test_old_json_defaults_strict_and_fixed_path():
    """New defaults preserve existing fields and reject unknown keys."""
    old = method()
    request = Simulation.model_validate(old.model_dump())
    assert request.mobile.mixer_ml == 0
    assert request.column.efficiency_model == "fixed"
    assert request.max_pressure_bar is None
    assert effective_plates(request.column, .3) == request.column.plates
    auto = simulate(request)
    explicit = simulate(request.model_copy(update={"solver": "analytic"}))
    assert auto["traces"] == explicit["traces"]
    assert auto["peaks"] == explicit["peaks"]
    with pytest.raises(ValidationError):
        Simulation.model_validate({**old.model_dump(), "unknown_physics": 1})


def test_mixer_step_and_ramp_mass_balance():
    """Compare tank integration to its step and ramp closed forms."""
    request = method()
    request.mobile.dwell_ml = 0
    request.mobile.mixer_ml = .06
    request.gradient[0].interpolation = "step"
    request.gradient[0].b_percent = 10
    request.gradient[1].time_min = 1
    request.gradient[1].b_percent = 90
    request.gradient[2].time_min = 5
    request.gradient[2].b_percent = 90
    program = Program(request)
    tau = .06/.3
    times = np.linspace(1, 5, 101)
    values = np.array([program.local_phi(t, 0, 0, 0) for t in times])
    expected = .9 - .8*np.exp(-(times-1)/tau)
    assert np.all(np.diff(values) >= -1e-12)
    np.testing.assert_allclose(values, expected, atol=1e-8)
    request.gradient[0].interpolation = "linear"
    request.gradient[1].time_min = 4
    program = Program(request)
    # Linear ramp tank solution y=phi0+m*(t-tau+tau*exp(-t/tau)).
    slope = .8/4
    for time_min in [1, 2, 3]:
        exact = .1+slope*(time_min-tau+tau*math.exp(-time_min/tau))
        assert program.local_phi(time_min, 0, 0, 0) == pytest.approx(exact, abs=1e-8)


def test_mixer_solver_and_single_case_delay():
    """A fixed increasing-ramp example takes ODE and delays with tank volume."""
    request = method()
    times = []
    for mixer in [0, .02, .08]:
        request.mobile.mixer_ml = mixer
        result = simulate(request)
        assert result["solver"] == ("ode" if mixer else "analytic")
        times.append(result["peaks"][0]["rt_min"])
    assert times[0] < times[1] < times[2]


def test_knox_minimum_and_scaling():
    """Analytic stationary point: C*y^6+(A/3)*y^4-B=0, y=nu^(1/3)."""
    from scipy.optimize import brentq

    column = method().column
    a, b, c = column.vd_a, column.vd_b, column.vd_c
    y = brentq(lambda value: c*value**6+a/3*value**4-b, .001, 100)
    nu = y**3
    derivative = lambda value: a/3*value**(-2/3)-b/value**2+c
    assert derivative(nu) == pytest.approx(0, abs=1e-10)
    assert derivative(nu*.5) < 0 < derivative(nu*2)
    column.efficiency_model = "van_deemter"
    plates = effective_plates(column, .3)
    assert effective_plates(column.model_copy(update={"length_mm": 200}), .3) == pytest.approx(2*plates)
    # At constant reduced velocity, doubling dp requires halving F.
    doubled = column.model_copy(update={"particle_um": column.particle_um*2})
    assert effective_plates(doubled, .15) == pytest.approx(plates/2)
    # At fixed F, dp also changes nu; inverse dp alone is not an identity.
    peak = simulate(method(column=column))["peaks"][0]
    assert peak["plates_used"] == pytest.approx(plates)


def test_viscosity_endpoints_pressure_scaling():
    """Test pure endpoints and Darcy proportionalities, not measured values."""
    column = method().column
    for solvent in ["ACN", "MeOH"]:
        for temperature in [0, 25, 60, 90, 100]:
            assert viscosity(0, solvent, temperature) == pytest.approx(water_viscosity(temperature))
            assert viscosity(1, solvent, temperature) == pytest.approx(organic_viscosity(solvent, temperature))
    pressure = column_pressure_bar(column, .3, .001)
    assert column_pressure_bar(column, .6, .001) == pytest.approx(2*pressure)
    assert column_pressure_bar(column, .3, .002) == pytest.approx(2*pressure)
    assert column_pressure_bar(column.model_copy(update={"length_mm": 200}), .3, .001) == pytest.approx(2*pressure)
    assert column_pressure_bar(column.model_copy(update={"particle_um": column.particle_um*2}), .3, .001) == pytest.approx(pressure/4)


def test_pressure_constraint_batch_and_mixer_budget():
    """Pressure flags constrain search but never suppress a single-run peak."""
    request = method()
    request.max_pressure_bar = .01
    result = simulate(request)
    assert result["traces"]
    assert any("超過上限" in warning for warning in result["warnings"])
    nodes = nodes_for(request, 5, [95], [10], 0, 3)
    batch = batch_max_pressure(request, [nodes])[0]
    scalar_method = request.model_copy(update={"gradient": nodes})
    assert batch == pytest.approx(pressure_profile(scalar_method, Program(scalar_method))["max_pressure_bar"], rel=1e-12)
    values = evaluate(request, [nodes])
    row = candidate(request, nodes, values, 0, .1, None)
    assert not row["feasible"]
    assert not row["pressure_feasible"]
    request.mobile.mixer_ml = .02
    with pytest.raises(ValidationError, match="2,000"):
        OptimizeMap(simulation=request)
    small = OptimizeMap(
        simulation=request,
        start_percent={"min":5,"max":5,"steps":1},
        end_percent={"min":95,"max":95,"steps":1},
        gradient_time_min={"min":10,"max":10,"steps":1},
    )
    start = time.monotonic()
    response = optimize_map(small)
    print(f"mixer_one_candidate_s={time.monotonic()-start:.6f}")
    assert response["solver"] == "ode"
    assert not response["top_candidates"][0]["pressure_feasible"]
