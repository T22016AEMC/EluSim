"""Bounded API/grid behavior with synthetic compounds."""

import json
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from elusim.main import app
from elusim.optimizer import optimize_map
from elusim.schemas import OptimizeMap
from test_engine import method


def map_request(**updates):
    """Create a small grid with invalid start/end pairs."""
    data = {
        "simulation": method(),
        "start_percent": {"min": 10, "max": 50, "steps": 3},
        "end_percent": {"min": 30, "max": 90, "steps": 3},
        "gradient_time_min": {"min": 2, "max": 20, "steps": 3},
    }
    return OptimizeMap.model_validate({**data, **updates})


def test_map_shapes_ranking_frontier_and_ode():
    """Check cube nulls, the ranking keys and nondominance of emitted points."""
    result = optimize_map(map_request())
    assert np.shape(result["min_rs"]) == (3, 3, 3)
    assert result["min_rs"][2][0][0] is None
    assert result["all_eluted"][2][0][0] is None
    assert result["evaluated"] == 21
    keys = [
        (
            not row["feasible"],
            row["run_time_min"] if row["run_time_min"] is not None else float("inf"),
            -(row["min_rs"] or 0),
        )
        for row in result["top_candidates"]
    ]
    assert keys == sorted(keys)
    assert len(result["top_candidates"]) == 10
    assert all(
        "max_rel_rt" in row["ode_check"] and "max_rel_sigma" in row["ode_check"]
        for row in result["top_candidates"]
    )
    for point in result["pareto"]:
        for other in result["pareto"]:
            dominates = (
                other["run_time_min"] <= point["run_time_min"]
                and other["min_rs"] >= point["min_rs"]
                and (
                    other["run_time_min"] < point["run_time_min"]
                    or other["min_rs"] > point["min_rs"]
                )
            )
            assert not dominates
    assert len(json.dumps(result).encode()) < 1048576


def test_map_limits_and_variable_flow_api():
    """Oversized work and nonconstant flow fail before a worker is started."""
    client = TestClient(app)
    payload = map_request().model_dump()
    payload["gradient_time_min"]["steps"] = 100
    payload["start_percent"] = {"min": 0, "max": 10, "steps": 30}
    payload["end_percent"] = {"min": 30, "max": 100, "steps": 30}
    assert client.post("/api/optimize/map", json=payload).status_code == 422
    payload = map_request().model_dump()
    payload["simulation"]["gradient"][-1]["flow_ml_min"] = 0.4
    response = client.post("/api/optimize/map", json=payload)
    assert response.status_code == 422
    assert "定流速" in response.text


def test_map_api_and_legacy_route():
    """The new worker kind returns calculations and the old route still exists."""
    client = TestClient(app)
    response = client.post("/api/optimize/map", json=map_request().model_dump())
    assert response.status_code == 200, response.text
    assert response.json()["solver"] == "analytic"
    assert any(route.path == "/api/optimize" for route in app.routes)


def test_twenty_thousand_candidates_five_compounds(request):
    """Record elapsed grid computation without interpreting model results."""
    base = method()
    base.compounds.extend(
        [
            base.compounds[0].model_copy(
                update={"id": "four", "name": "Synthetic D", "logkw": 2.7}
            ),
            base.compounds[1].model_copy(
                update={"id": "five", "name": "Synthetic E", "logkw": 3.3}
            ),
        ]
    )
    grid_request = map_request(
        simulation=base,
        start_percent={"min": 0, "max": 10, "steps": 20},
        end_percent={"min": 30, "max": 100, "steps": 25},
        gradient_time_min={"min": 2, "max": 60, "steps": 40},
    )
    terminal = request.config.pluginmanager.get_plugin("terminalreporter")
    result = optimize_map(grid_request)
    if terminal is not None:
        terminal.write_line(
            "map_performance: candidates=20000 compounds=5 elapsed_s="
            + str(result["elapsed_s"])
        )
    assert result["evaluated"] == 20000
    assert result["elapsed_s"] < 10
    import os
    from pathlib import Path

    if os.environ.get("ELUSIM_REVIEW_DIR"):
        (Path(os.environ["ELUSIM_REVIEW_DIR"]) / "map-performance.json").write_text(
            json.dumps(
                {"evaluated": 20000, "compounds": 5, "elapsed_s": result["elapsed_s"]},
                indent=2,
            ),
            encoding="utf8",
        )
