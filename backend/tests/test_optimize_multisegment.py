"""Seeded differential-evolution behavior using synthetic inputs."""

import pytest

from elusim.optimizer import optimize_multisegment
from elusim.schemas import OptimizeMultiSegment
from test_engine import method


@pytest.mark.parametrize("segments", [2, 3])
def test_monotone_nodes_and_reproducible_seed(segments):
    """Identical seeds and unconstrained elapsed budgets reproduce calculations."""
    request = OptimizeMultiSegment(
        simulation=method(),
        segments=segments,
        time_budget_s=25,
        total_gradient_time_bounds=(4, 8),
    )
    first = optimize_multisegment(request)
    second = optimize_multisegment(request)
    assert not first["time_budget_stopped"]
    assert first["gradient"] == second["gradient"]
    assert first["min_rs"] == second["min_rs"]
    nodes = first["gradient"]
    assert len(nodes) == segments + 2
    assert all(
        left["b_percent"] <= right["b_percent"] for left, right in zip(nodes, nodes[1:])
    )
    assert all(
        left["time_min"] < right["time_min"] for left, right in zip(nodes, nodes[1:])
    )
    assert "ode_check" in first
    assert first["evaluations"] > 0


def test_budget_stop_and_initial_candidate():
    """A tiny wall-clock allowance returns the best evaluated candidate and flag."""
    base = method()
    request = OptimizeMultiSegment(
        simulation=base, time_budget_s=0.00001, initial_candidate=base.gradient
    )
    result = optimize_multisegment(request)
    assert result["time_budget_stopped"]
    assert result["evaluations"] >= 1
    assert result["iterations"] >= 1


def test_cancelled_process_releases_slot():
    """A pre-set cancellation signal terminates a worker and frees its slot."""
    import threading

    from elusim.jobs import compute

    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(RuntimeError, match="cancelled"):
        compute(
            "optimization_multisegment",
            OptimizeMultiSegment(simulation=method()).model_dump(),
            cancelled=cancelled,
        )
    result = compute("simulation", method().model_dump())
    assert len(result["order"]) == 3


@pytest.mark.parametrize("segments", [2, 3])
def test_minimum_duration_parameterization(segments):
    """Decode 200 seeded vectors without violating duration or monotonicity."""
    import numpy as np
    from elusim.optimizer import decode_multisegment

    generator = np.random.default_rng(42)
    for _ in range(200):
        minimum = float(generator.uniform(0.1, 10))
        request = OptimizeMultiSegment(
            simulation=method(),
            segments=segments,
            min_segment_min=minimum,
            total_gradient_time_bounds=(0.1, 60),
        )
        assert request.total_gradient_time_bounds[0] == segments * minimum
        parameters = [
            generator.uniform(0, 50),
            generator.uniform(),
            *generator.uniform(size=segments - 1),
            *generator.uniform(0.001, 1, size=segments),
            generator.uniform(segments * minimum, 60),
        ]
        nodes = decode_multisegment(request, request.simulation, parameters)
        durations = np.diff([node.time_min for node in nodes[: segments + 1]])
        assert np.all(durations >= minimum - 1e-9)
        assert durations.sum() == pytest.approx(parameters[-1], abs=1e-9)
        assert all(
            left.b_percent <= right.b_percent for left, right in zip(nodes, nodes[1:])
        )


def test_minimum_duration_bounds_rejected():
    """Reject impossible totals and out-of-range minimum segment values."""
    from pydantic import ValidationError

    for minimum in [0.09, 10.01]:
        with pytest.raises(ValidationError):
            OptimizeMultiSegment(simulation=method(), min_segment_min=minimum)
    with pytest.raises(ValidationError):
        OptimizeMultiSegment(
            simulation=method(),
            segments=3,
            min_segment_min=1,
            total_gradient_time_bounds=(0.1, 2),
        )
