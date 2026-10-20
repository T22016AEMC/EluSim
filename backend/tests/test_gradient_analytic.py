"""Equation and API regression checks; synthetic inputs only."""
import json
import math
from pathlib import Path

import pytest

from elusim.engine import Program, outlet_slope, retention, retention_state, simulate, volume
from elusim.schemas import Simulation

CASES = [
    ('zero_dwell', 2.0, 4.0, 0.10, 0.50, 10.0, 0.0),
    ('with_dwell', 2.5, 5.0, 0.10, 0.60, 8.0, 0.12),
    ('short_gradient', 3.0, 6.0, 0.05, 0.80, 5.0, 0.30),
    ('long_gradient', 1.5, 3.0, 0.20, 0.50, 20.0, 0.60),
    ('early_isocratic', -0.5, 2.0, 0.10, 0.50, 10.0, 1.20),
    ('zero_s', 1.0, 0.0, 0.10, 0.60, 10.0, 0.0),
]
COMPARISONS = []


def linear_method(case, compression='poppe'):
    """Build a constant-flow, plug-flow synthetic method with no mixing."""
    name, logkw, strength, phi0, phi1, duration, dwell = case
    return Simulation.model_validate({
        'band_compression': compression,
        'compounds': [{'id': name, 'name': name, 'logkw': logkw, 's': strength}],
        'column': {'void_ml': 0.3, 'plates': 12000},
        'mobile': {'dwell_ml': dwell, 'injection_ul': 0, 'extra_sigma_min': 0},
        'gradient': [
            {'time_min': 0, 'b_percent': 100 * phi0},
            {'time_min': duration, 'b_percent': 100 * phi1},
            {'time_min': max(40, duration + 10), 'b_percent': 100 * phi1},
        ],
    })


def analytic_values(case, compression='poppe'):
    """Evaluate the closed-form equations supplied in the P0 specification."""
    _, logkw, strength, phi0, phi1, duration, dwell = case
    t0 = 1.0
    delay = dwell / 0.3
    k0 = 10 ** (logkw - strength * phi0)
    steepness = t0 * (phi1 - phi0) * strength * math.log(10) / duration
    if k0 <= delay / t0 or steepness == 0:
        rt_min = t0 * (1 + k0)
        k_e = k0
        factor = 1.0
    else:
        denominator = steepness * (k0 - delay / t0) + 1
        rt_min = t0 / steepness * math.log(denominator) + t0 + delay
        k_e = k0 / denominator
        poppe_p = k0 * steepness / (1 + k0)
        factor = math.sqrt((1 + poppe_p + poppe_p**2 / 3) / (1 + poppe_p)**2)
    if compression == 'none':
        factor = 1.0
    return rt_min, factor * t0 * (1 + k_e) / math.sqrt(12000)


@pytest.fixture(scope='module', autouse=True)
def save_equation_comparisons(tmp_path_factory):
    """Write raw mathematical comparisons for the implementation report."""
    yield
    destination = tmp_path_factory.mktemp('phase1-equations') / 'gradient-analytic-comparison.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(COMPARISONS, indent=2), encoding='utf8')


@pytest.mark.parametrize('case', CASES, ids=[case[0] for case in CASES])
def test_linear_gradient_closed_form(case):
    """Check migration and local width against the specified analytic expressions."""
    method = linear_method(case)
    expected_rt, expected_sigma = analytic_values(case)
    peak = simulate(method)['peaks'][0]
    assert peak['rt_min'] == pytest.approx(expected_rt, rel=1e-5)
    assert peak['sigma_col_min'] == pytest.approx(expected_sigma, rel=1e-3)
    assert retention(method, method.compounds[0]) == pytest.approx(peak['rt_min'], rel=1e-7)
    without = simulate(linear_method(case, 'none'))['peaks'][0]
    assert without['compression_factor'] == 1
    assert without['sigma_col_min'] == pytest.approx(analytic_values(case, 'none')[1], rel=1e-3)
    COMPARISONS.append({
        'case': case[0],
        'parameters': dict(zip(['logkw', 's', 'phi0', 'phi1', 'tG_min', 'dwell_ml'], case[1:])),
        'rt_theory_min': expected_rt,
        'rt_program_min': peak['rt_min'],
        'rt_relative_error': abs(peak['rt_min'] / expected_rt - 1),
        'sigma_col_theory_min': expected_sigma,
        'sigma_col_program_min': peak['sigma_col_min'],
        'sigma_col_relative_error': abs(peak['sigma_col_min'] / expected_sigma - 1),
    })


def test_isocratic_width_identity_and_variance_addition():
    """Check G=1 and the original isocratic width and additive variance identities."""
    method = linear_method(('isocratic', 2, 4, 0.3, 0.3, 10, 0))
    peak = simulate(method)['peaks'][0]
    assert peak['compression_factor'] == 1
    assert peak['sigma_min'] == pytest.approx(peak['rt_min'] / math.sqrt(12000), rel=1e-7)
    method.mobile.injection_ul = 2
    method.mobile.extra_sigma_min = 0.02
    with_extras = simulate(method)['peaks'][0]
    assert with_extras['sigma_min']**2 == pytest.approx(
        peak['sigma_min']**2 + (0.002 / 0.3)**2 / 12 + 0.02**2
    )


def test_outlet_state_and_right_hand_step_derivative():
    """A composition jump must not be used as an infinite local ramp."""
    method = linear_method(CASES[0])
    method.gradient[0].interpolation = 'step'
    method.gradient[1].time_min = 2
    program = Program(method)
    assert outlet_slope(program, 3, volume(method.column), 0) == pytest.approx(0, abs=1e-9)
    state = retention_state(method, method.compounds[0])
    assert state.phi_outlet == program.local_phi(state.rt_min, 1, volume(method.column), 0)
    assert state.flow_at_elution == program.flow(state.rt_min)
    assert state.k_e == pytest.approx(10 ** (2 - 4 * state.phi_outlet))
