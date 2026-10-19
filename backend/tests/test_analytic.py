"""Synthetic equation comparisons; no experimental data are used."""

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from elusim.analytic import analytic_batch, analytic_state
from elusim.engine import Program, band_width, retention_state, simulate, volume
from elusim.schemas import Simulation
from test_gradient_analytic import CASES, analytic_values, linear_method


@pytest.mark.parametrize("case", CASES, ids=[case[0] for case in CASES])
def test_linear_equations(case):
    """Compare closed-form migration and widths to the supplied identities."""
    method = linear_method(case)
    program = Program(method)
    state = analytic_state(
        program.t,
        program.phi,
        program.step,
        method.compounds[0].logkw,
        method.compounds[0].s,
        program.f,
        volume(method.column),
        method.mobile.dwell_ml,
    )
    expected_rt, expected_width = analytic_values(case)
    assert state.rt_min == pytest.approx(expected_rt, rel=1e-9)
    assert band_width(method, method.compounds[0], state, program)[
        "sigma_col_min"
    ] == pytest.approx(expected_width, rel=1e-9)


def test_random_programs_and_batch(tmp_path):
    """Compare 220 seeded hold/ramp/step programs to the independent ODE path."""
    generator = np.random.default_rng(42)
    rows = []
    for index in range(220):
        ramps = int(generator.integers(1, 4))
        flow = float(generator.uniform(0.2, 1))
        dwell = 0.0 if index == 0 else float(generator.uniform(0, 2))
        phi = float(generator.uniform(0.02, 0.25))
        hold = float(generator.uniform(0.1, 2))
        nodes = [
            {"time_min": 0, "b_percent": phi * 100, "flow_ml_min": flow},
            {"time_min": hold, "b_percent": phi * 100, "flow_ml_min": flow},
        ]
        elapsed = hold
        for ramp in range(ramps):
            nodes[-1]["interpolation"] = (
                "step" if index % 4 == 0 and ramp == 0 else "linear"
            )
            elapsed += float(generator.uniform(1, 8))
            phi += (0.95 - phi) / (ramps - ramp)
            nodes.append(
                {"time_min": elapsed, "b_percent": phi * 100, "flow_ml_min": flow}
            )
        nodes.append({**nodes[-1], "time_min": elapsed + 12})
        method = Simulation.model_validate(
            {
                "compounds": [
                    {
                        "id": "synthetic",
                        "name": "Synthetic",
                        "logkw": float(generator.uniform(0.1, 4.5)),
                        "s": float(generator.uniform(2, 9)),
                    }
                ],
                "column": {"void_ml": float(generator.uniform(0.1, 0.5))},
                "mobile": {"dwell_ml": dwell, "injection_ul": 0},
                "gradient": nodes,
            }
        )
        program = Program(method)
        compound = method.compounds[0]
        analytic = analytic_state(
            program.t,
            program.phi,
            program.step,
            compound.logkw,
            compound.s,
            program.f,
            volume(method.column),
            dwell,
        )
        batch = analytic_batch(
            program.t,
            program.phi,
            program.step,
            [compound.logkw],
            [compound.s],
            flow,
            volume(method.column),
            dwell,
        )
        for field in ("rt_min", "phi_outlet", "k_e", "dphi_dt_outlet"):
            assert batch[field][0, 0] == pytest.approx(
                getattr(analytic, field), rel=1e-12, abs=1e-12
            )
        ode = retention_state(method, compound, rtol=1e-10, max_step=0.05)
        finite = analytic.rt_min <= program.t[-1]
        assert finite == (ode is not None)
        width = band_width(method, compound, analytic, program)["sigma_col_min"]
        ode_width = (
            band_width(method, compound, ode, program)["sigma_col_min"] if ode else None
        )
        rt_difference = abs(analytic.rt_min / ode.rt_min - 1) if ode else None
        width_difference = abs(width / ode_width - 1) if ode else None
        if ode:
            assert rt_difference <= 1e-5
            assert width_difference <= 1e-4
        rows.append(
            {
                "case": index,
                "nodes": json.dumps(nodes, separators=(",", ":")),
                "logkw": compound.logkw,
                "s": compound.s,
                "flow": flow,
                "void_ml": volume(method.column),
                "dwell": dwell,
                "rt_analytic": analytic.rt_min,
                "rt_ode": ode.rt_min if ode else None,
                "sigma_analytic": width,
                "sigma_ode": ode_width,
                "rt_relative_difference": rt_difference,
                "sigma_relative_difference": width_difference,
                "eluted": finite,
            }
        )
    # Tests write disposable files; the review export script chooses the output path.
    import os

    destination = Path(os.environ.get("ELUSIM_REVIEW_DIR", str(tmp_path)))
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / "analytic-vs-ode.csv").open(
        "w", newline="", encoding="utf8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_variable_flow_and_finite_window():
    """Variable flow falls back to ODE; analytic and ODE share the time window."""
    method = linear_method(CASES[0])
    method.gradient[-1].flow_ml_min = 0.4
    program = Program(method)
    assert (
        analytic_state(
            program.t,
            program.phi,
            program.step,
            2,
            4,
            program.f,
            volume(method.column),
            0,
        )
        is None
    )
    assert simulate(method)["solver"] == "ode"
    method = linear_method(CASES[0])
    method.gradient = method.gradient[:2]
    method.gradient[-1].time_min = 0.1
    assert not simulate(method)["peaks"][0]["eluted"]
    assert not simulate(method.model_copy(update={"solver": "ode"}))["peaks"][0][
        "eluted"
    ]


def test_batch_candidates_steps_and_decreasing_ramps():
    """Batch candidate axes preserve independent programs and negative slopes."""
    times = np.array([[0, 1, 3, 7], [0, 2, 4, 8]], dtype=float)
    phis = np.array([[0.1, 0.1, 0.8, 0.8], [0.8, 0.8, 0.2, 0.2]])
    steps = np.array([[False, True, False, False], [False] * 4])
    result = analytic_batch(times, phis, steps, [1, 3], [0, 4], 0.3, 0.3, 0.2)
    for candidate in range(2):
        for compound, (logkw, strength) in enumerate(((1, 0), (3, 4))):
            scalar = analytic_state(
                times[candidate],
                phis[candidate],
                steps[candidate],
                logkw,
                strength,
                0.3,
                0.3,
                0.2,
            )
            assert result["rt_min"][candidate, compound] == pytest.approx(
                scalar.rt_min, rel=1e-12
            )
