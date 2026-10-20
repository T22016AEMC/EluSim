"""Fit the requested regression using repository curves only; no network access."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from elusim.generic_lss import FEATURE_NAMES, FEATURE_VERSION, PENDING_STATUS, generic_features

SEED = 42
RIDGE_ALPHA = 1.0


def least_squares(design, target):
    """Fit an unpenalized intercept with ordinary least squares."""
    return np.linalg.lstsq(design, target, rcond=None)[0]


def metrics(actual, predicted):
    """Return numbers without a scientific interpretation."""
    residual = predicted - actual
    return {
        'mae': float(np.mean(np.abs(residual))),
        'rmse': float(np.sqrt(np.mean(residual**2))),
    }


def fit():
    """Group whole curves by Murcko scaffold and fit only training groups."""
    source = ROOT / 'data/retention/curves.json'
    rows = json.loads(source.read_text(encoding='utf8'))
    features = [generic_features(row['smiles']) for row in rows]
    scaffolds = [
        MurckoScaffold.MurckoScaffoldSmiles(mol=Chem.MolFromSmiles(item['canonical_smiles'])) or '<acyclic>'
        for item in features
    ]
    groups = np.array(sorted(set(scaffolds)))
    np.random.default_rng(SEED).shuffle(groups)
    test_count = max(1, int(np.ceil(len(groups) * 0.2)))
    test_groups = set(groups[:test_count])
    test = np.array([scaffold in test_groups for scaffold in scaffolds])
    train = ~test
    assert train.any() and test.any()
    assert not set(np.array(scaffolds)[train]) & set(np.array(scaffolds)[test])
    canonical = np.array([item['canonical_smiles'] for item in features])
    assert not set(canonical[train]) & set(canonical[test])
    matrix = np.array([[item[name] for name in FEATURE_NAMES] for item in features], dtype=float)
    means = matrix[train].mean(axis=0)
    scales = matrix[train].std(axis=0)
    scales[scales == 0] = 1
    design = np.column_stack([np.ones(len(rows)), (matrix - means) / scales])
    logkw = np.array([row['logkw'] for row in rows])
    strength = np.array([row['s'] for row in rows])
    penalty = np.eye(design.shape[1]) * RIDGE_ALPHA
    penalty[0, 0] = 0
    coefficients = np.linalg.solve(design[train].T @ design[train] + penalty, design[train].T @ logkw[train])
    fitted_logkw = design @ coefficients
    s_design = np.column_stack([np.ones(len(rows)), fitted_logkw])
    s_coefficients = least_squares(s_design[train], strength[train])
    fitted_s = s_design @ s_coefficients
    # The requested deployed S equation omits sqrt(MW). Both numeric comparisons
    # are written below; the extra term is not selected using test-group results.
    # Seed 42 S test MAE: logKw-only 0.8094459858642059; +sqrt(MW) 0.7951952797418455.
    # Seed 42 S test RMSE: logKw-only 1.043564550698119; +sqrt(MW) 1.0115544771677827.
    # These are raw fit outputs; the requested deployed S equation remains two coefficients.
    extra_s_design = np.column_stack([s_design, matrix[:, -1]])
    extra_s_coefficients = least_squares(extra_s_design[train], strength[train])
    extra_s_fitted = extra_s_design @ extra_s_coefficients
    summary = {
        'seed': SEED,
        'rows': len(rows),
        'train_rows': int(train.sum()),
        'test_rows': int(test.sum()),
        'scaffolds': len(groups),
        'train_scaffolds': int(len(groups) - test_count),
        'test_scaffolds': test_count,
        'ridge_alpha': RIDGE_ALPHA,
    }
    for label, mask in [('train', train), ('test', test)]:
        summary[label] = {
            'logkw': metrics(logkw[mask], fitted_logkw[mask]),
            's': metrics(strength[mask], fitted_s[mask]),
            's_with_sqrt_mw': metrics(strength[mask], extra_s_fitted[mask]),
        }
    model = {
        'model_id': 'generic-lss',
        'model_version': '1.0.0',
        'feature_version': FEATURE_VERSION,
        'feature_names': FEATURE_NAMES,
        'validation_status': PENDING_STATUS,
        'standardization': {'mean': means.tolist(), 'scale': scales.tolist()},
        'logkw': {'intercept': float(coefficients[0]), 'coefficients': coefficients[1:].tolist(), 'ridge_alpha': RIDGE_ALPHA},
        's': {'intercept': float(s_coefficients[0]), 'logkw_coefficient': float(s_coefficients[1])},
        'bounds': {'logkw': [-3, 12], 's': [0, 30]},
        'split': {'seed': SEED, 'test_fraction': 0.2, 'group': 'Murcko scaffold; acyclic structures in one group', 'test_scaffolds': sorted(test_groups), 'fit_uses': 'train groups only'},
        'data_source': {
            'path': 'data/retention/curves.json',
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'rows': len(rows),
            'reference': rows[0]['reference'],
            'license': 'CC BY-NC-SA 3.0 US',
            'attribution': 'Boswell retention database; Wiczling curation; existing repository LSS curve fits',
        },
        'scope': rows[0]['scope'],
        'phi_range': rows[0]['phi_range'],
        'particle_um': rows[0]['applicability_domain']['particle_um'],
        'application_notes': [
            'Generic RP-C18 regression; non-commercial use under the data license.',
            'Training input: ACN / Eclipse Plus C18 / 35 C / 0.1% formic acid / phi 0.2-0.5.',
            'Other conditions are extrapolation; no pKa or ionization correction.',
            'S uses fitted logKw; sqrt(MW) alternative numbers are in the summary only.',
        ],
    }
    (ROOT / 'backend/models/generic-lss.json').write_text(json.dumps(model, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    (output / 'generic-lss-fit-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf8')
    with (output / 'generic-lss-fit.csv').open('w', encoding='utf8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            'smiles', 'canonical_smiles', 'scaffold', 'split',
            'crippen_logp', 'tpsa', 'hbd', 'aromatic_rings', 'mw', 'sqrt_mw',
            'logkw', 's', 'logkw_fitted', 's_fitted', 'logkw_residual', 's_residual',
        ])
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow({
                'smiles': row['smiles'], 'canonical_smiles': canonical[index],
                'scaffold': scaffolds[index], 'split': 'test' if test[index] else 'train',
                **{name: features[index][name] for name in ['crippen_logp', 'tpsa', 'hbd', 'aromatic_rings', 'mw', 'sqrt_mw']},
                'logkw': row['logkw'], 's': row['s'],
                'logkw_fitted': fitted_logkw[index], 's_fitted': fitted_s[index],
                'logkw_residual': fitted_logkw[index] - row['logkw'],
                's_residual': fitted_s[index] - row['s'],
            })
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    fit()
