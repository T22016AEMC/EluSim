"""Scoped measured curves and QSRR are separate from method-specific Rt."""
import json,pathlib,functools
from .features import molecular_features
from .conditions import scope_matches, scope_mismatches
from .schemas import Scope
from .sources import source_code
DATA=pathlib.Path(__file__).resolve().parents[2]/'data/retention'
@functools.lru_cache(maxsize=1)
def measured_curves():
    return json.loads((DATA/'curves.json').read_text(encoding='utf8'))

def predict_curve(smiles, method, use_literature=True):
    """Keep explicit curve/QSRR queries, reporting method differences as notices."""
    from .prediction import infer, load_model
    from .generic_lss import PENDING_STATUS
    import numpy as np

    features, _ = molecular_features(smiles)
    metadata = load_model('lss-parameters')['metadata']
    scope = metadata['scope']
    limits = metadata['phi_range']
    result = {
        'status': 'Insufficient data', 'output_type': 'lss_parameters',
        'logkw': None, 's': None, 'rt_min': None, 'features': features,
        'model': {key: value for key, value in metadata.items() if not key.endswith('_smiles')},
        'input_conditions': method.model_dump(), 'warnings': list(metadata['limitations']),
        'scope': {key: value for key, value in scope.items() if key != 'mode'},
        'phi_range': limits, 'curve': None, 'parameter_source': None,
        'applicability': {'accepted': False}, 'validation_status': PENDING_STATUS,
    }
    mismatches = scope_mismatches(scope, method)
    specification = curve_conditions()
    if method.column.particle_um != specification['particle_um']:
        mismatches.append(f"particle_um: current {method.column.particle_um}; source {specification['particle_um']}")
    for index, node in enumerate(method.gradient):
        if not limits[0] <= node.b_percent / 100 <= limits[1]:
            mismatches.append(f'gradient[{index}].b_percent: current {node.b_percent}; source interval {100 * limits[0]}–{100 * limits[1]}')
    result['condition_mismatches'] = mismatches
    result['warnings'].extend(mismatches)
    if method.mode != 'RP':
        result['warnings'].append('LSS parameter prediction supports RP mode only')
        return result
    known = None
    if use_literature:
        known = next((row for row in measured_curves() if row['smiles'] == features['canonical_smiles']), None)
    if known is not None:
        logkw, strength = known['logkw'], known['s']
        result.update(
            status='Literature-derived',
            parameter_source='Measured isocratic log10(k) curve fitted to LSS',
            observations=known['observations'], fit_rmse_logk=known['fit_rmse_logk'],
        )
        result['applicability'] = {
            'accepted': True,
            'rule': 'Exact canonical structure in the stored curve database; method differences reported separately',
            'seen_in_training': features['canonical_smiles'] in metadata['train_smiles'],
        }
    else:
        predicted = infer('lss-parameters', smiles)
        result.update({key: predicted[key] for key in ['status', 'applicability']})
        result['warnings'].extend(predicted['warnings'])
        if predicted['prediction'] is None:
            return result
        logkw, strength = predicted['prediction']
        result['parameter_source'] = 'Existing scoped QSRR; not measured for this query'
    if not -3 <= logkw <= 12 or not 0 <= strength <= 30:
        result['warnings'].append('Predicted parameters outside schema bounds; output withheld')
        result['status'] = 'Insufficient data'
        return result
    fractions = np.linspace(*limits, 31)
    result.update(
        logkw=float(logkw), s=float(strength),
        curve={
            'phi': fractions.tolist(), 'k': (10 ** (logkw - strength * fractions)).tolist(),
            'logk': (logkw - strength * fractions).tolist(), 'logarithm_base': 10,
        },
    )
    return result


def resolve_compounds(req, overwrite_manual=False):
    """Resolve shared compound IDs while preserving calibration and manual edits."""
    from .estimation import apply_estimate, estimate_retention, parameter_tier

    compounds = []
    records = []
    for compound in req.compounds:
        tier = parameter_tier(compound)
        manual_locked = compound.parameter_tier == 'M' or (
            compound.parameter_origin == 'manual'
            and (compound.logkw is not None or compound.s is not None)
        )
        if tier == 'D' or (manual_locked and not overwrite_manual):
            compounds.append(compound)
            records.append({
                'compound_id': compound.id,
                'status': 'Calibration parameters preserved' if tier == 'D' else 'Manual parameters preserved',
                'reason': 'Calibration has priority' if tier == 'D' else 'Explicit overwrite confirmation required',
            })
            continue
        if compound.kind != 'small_molecule' or not compound.smiles:
            compounds.append(compound)
            records.append({'compound_id': compound.id, 'status': 'Insufficient data', 'reason': 'Small-molecule SMILES required'})
            continue
        try:
            result = estimate_retention(compound.smiles, req)
            compounds.append(apply_estimate(compound, result))
            records.append({'compound_id': compound.id, **result})
        except (ValueError, OSError, KeyError) as exc:
            compounds.append(compound)
            records.append({'compound_id': compound.id, 'status': 'Insufficient data', 'reason': str(exc)})
    return req.model_copy(update={'compounds': compounds, 'workflow': 'known'}), records


def curve_conditions():
    """Expose existing model metadata and documented material specification, not a new model."""
    from .prediction import load_model
    meta=load_model('lss-parameters')['metadata']
    return {'model_id':meta['model_id'],'model_version':meta['model_version'],
            'scope':meta['scope'],'phi_range':meta['phi_range'],
            'particle_um':measured_curves()[0]['applicability_domain']['particle_um'],
            'status':'Experimental model prediction','limitations':meta['limitations'],
            'notice':'Matching training conditions does not establish external gradient accuracy.'}
