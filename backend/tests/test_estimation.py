"""Tier routing, equations, provenance and API behavior; no experimental claims."""
import csv
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from elusim.engine import simulate
from elusim.estimation import estimate_retention
from elusim.generic_lss import FEATURE_NAMES, PENDING_STATUS, generic_estimate, generic_features, load_generic_model
from elusim.main import app, _rates
from elusim.retention_registry import resolve_compounds
from elusim.schemas import Compound
from test_engine import method

CAFFEINE = 'Cn1cnc2c1c(=O)n(C)c(=O)n2C'
NONLOOKUP = 'CC(=O)Nc1ccc(OCCC)cc1'


@pytest.fixture(autouse=True)
def reset_rates():
    """Keep independent API cases below the unchanged request budget."""
    _rates.clear()


@pytest.mark.parametrize('smiles,tier', [(CAFFEINE, 'A'), (NONLOOKUP, 'B'), ('[Na+]', 'C')])
def test_tiers_return_parameters_under_default_conditions(smiles, tier):
    """Default chemistry differences must be exposed rather than blocking output."""
    request = method()
    result = estimate_retention(smiles, request)
    assert result['tier'] == tier
    assert result['validation_status'] == PENDING_STATUS
    assert -3 <= result['logkw'] <= 12 and 0 <= result['s'] <= 30
    assert result['condition_differences'] and result['warnings']
    request.compounds = [Compound(id='query', name='Query', smiles=smiles)]
    request.workflow = 'structure'
    output = simulate(request)
    assert output['peaks'][0]['parameter_tier'] == tier
    assert output['peaks'][0]['rt_min'] is not None
    assert max(output['traces'][0]['y']) > 0
    assert output['peaks'][0]['warning']


def test_estimate_api_invalid_smiles_and_other_modes():
    """Check the new endpoint and its explicit error cases."""
    client = TestClient(app)
    data = {'smiles': CAFFEINE, 'method': method().model_dump()}
    response = client.post('/api/retention/estimate', json=data)
    assert response.status_code == 200 and response.json()['tier'] == 'A'
    data['smiles'] = 'not-a-smiles'
    assert client.post('/api/retention/estimate', json=data).status_code == 422
    data['smiles'] = CAFFEINE
    data['method']['mode'] = 'HILIC'
    assert client.post('/api/retention/estimate', json=data).status_code == 422


def test_generic_equation_and_clipping(monkeypatch):
    """Compare NumPy inference to the stored linear equations and exercise bounds."""
    features = generic_features('CCO')
    model = load_generic_model()
    vector = np.array([features[name] for name in model['feature_names']])
    standardized = (vector - model['standardization']['mean']) / model['standardization']['scale']
    expected_kw = model['logkw']['intercept'] + np.dot(model['logkw']['coefficients'], standardized)
    expected_s = model['s']['intercept'] + model['s']['logkw_coefficient'] * expected_kw
    actual_kw, actual_s, _ = generic_estimate(features)
    assert actual_kw == pytest.approx(np.clip(expected_kw, -3, 12))
    assert actual_s == pytest.approx(np.clip(expected_s, 0, 30))
    changed = json.loads(json.dumps(model))
    changed['logkw']['intercept'] = 1000
    changed['s']['intercept'] = -1000
    changed['s']['logkw_coefficient'] = 0
    monkeypatch.setattr('elusim.generic_lss.load_generic_model', lambda: changed)
    kw, strength, warnings = generic_estimate(features)
    assert (kw, strength) == (12, 0)
    assert len(warnings) == 2 and all('clipped' in warning for warning in warnings)


def test_generic_warnings_include_methanol_and_ionization():
    """Check fixed and conditional notices on the generic fallback."""
    request = method()
    request.mobile.b = 'MeOH'
    result = estimate_retention('[Na+]', request)
    assert result['tier'] == 'C'
    assert any('非實測' in warning for warning in result['warnings'])
    assert any('MeOH' in warning for warning in result['warnings'])
    assert any('pKa' in warning for warning in result['warnings'])
    assert any('mobile_b' in difference for difference in result['condition_differences'])


def test_manual_and_calibration_priority():
    """Auto resolution never replaces complete manual or calibration records."""
    request = method()
    request.compounds = [
        Compound(id='manual', name='Manual', smiles=CAFFEINE, logkw=2, s=4, parameter_tier='M'),
        Compound(id='calibration', name='Calibration', smiles=CAFFEINE, logkw=3, s=5, parameter_tier='D', parameter_origin='calibration', source='calibrated'),
    ]
    resolved, _ = resolve_compounds(request)
    assert [compound.logkw for compound in resolved.compounds] == [2, 3]
    replaced, _ = resolve_compounds(request, overwrite_manual=True)
    assert replaced.compounds[0].parameter_tier == 'A'
    assert replaced.compounds[1].logkw == 3 and replaced.compounds[1].parameter_tier == 'D'
    request.compounds[0].s = None
    request.compounds[1].s = None
    incomplete, _ = resolve_compounds(request)
    assert all(compound.s is None for compound in incomplete.compounds)
    explicit, _ = resolve_compounds(request, overwrite_manual=True)
    assert explicit.compounds[0].s is not None
    assert explicit.compounds[1].s is None


def test_fit_groups_and_standardization_use_training_rows_only():
    """Check scaffold/structure isolation and artifact arithmetic, not prediction quality."""
    root = Path(__file__).resolve().parents[2]
    with (root / 'artifacts/generic-lss-fit.csv').open(encoding='utf8') as handle:
        rows = list(csv.DictReader(handle))
    training = [row for row in rows if row['split'] == 'train']
    test = [row for row in rows if row['split'] == 'test']
    assert not {row['scaffold'] for row in training} & {row['scaffold'] for row in test}
    assert not {row['canonical_smiles'] for row in training} & {row['canonical_smiles'] for row in test}
    values = np.array([
        [generic_features(row['smiles'])[name] for name in load_generic_model()['feature_names']]
        for row in training
    ])
    assert np.allclose(values.mean(axis=0), load_generic_model()['standardization']['mean'])
    assert load_generic_model()['validation_status'] == PENDING_STATUS
    assert len(rows) == 273
