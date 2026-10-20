"""Fixed software gates for tier C; empirical review remains with the user."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "tier_c_candidates", ROOT / "scripts/fit_tier_c_candidates.py"
)
CANDIDATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CANDIDATES)

from elusim.generic_lss import generic_estimate, generic_features, load_generic_model


@pytest.fixture(scope="module")
def tier_c_rows():
    """Force generic inference without measured-curve or QSRR routing."""
    outputs = [
        generic_estimate(generic_features(smiles)) for _, smiles in CANDIDATES.MOLECULES
    ]
    return CANDIDATES.simulation_rows(
        [row[0] for row in outputs],
        [row[1] for row in outputs],
        ["C"] * len(outputs),
    )


@pytest.mark.parametrize("index", range(19))
def test_forced_tier_c_fixed_gates(tier_c_rows, index):
    """Enforce each preregistered gate using the default program and solver."""
    gate = CANDIDATES.gate_rows(tier_c_rows)[index]
    assert gate["passed"], json.dumps(gate)


def test_transformed_equation_identity():
    """The stored logKw equation must equal the algebraic logk35 inversion."""
    model = load_generic_model()
    assert model["selected_candidate"] == "C2"
    for _, smiles in CANDIDATES.MOLECULES:
        features = generic_features(smiles)
        matrix = np.array([[features[key] for key in model["feature_names"]]])
        target = CANDIDATES.equation_predict(model["target_equation"], matrix)[0]
        slope = model["s"]["logkw_coefficient"]
        intercept = model["s"]["intercept"]
        expected = (target + 0.35 * intercept) / (1 - 0.35 * slope)
        value, strength, _ = generic_estimate(features)
        assert value == pytest.approx(expected, abs=1e-12)
        assert value - 0.35 * strength == pytest.approx(target, abs=1e-12)


def test_candidate_signs_and_outer_split():
    """Inspect slope bounds and the unchanged outer scaffold partition."""
    details = json.loads(
        (ROOT / "review/phase2.1/tier-c-candidate-details.json").read_text(
            encoding="utf-8"
        )
    )
    old = json.loads(
        (ROOT / "backend/models/generic-lss-v1.json").read_text(encoding="utf-8")
    )
    assert details["test_scaffolds"] == old["split"]["test_scaffolds"]
    for candidate in details["candidates"]:
        coefficients = candidate["equation"]["coefficients"]
        assert coefficients[1] >= 0
        assert coefficients[2] <= 0
        assert coefficients[3] <= 0
    assert details["selected"] == "C2"
