"""Tiered parameter acquisition; method differences are retained as warnings."""
import numpy as np

from .conditions import scope_mismatches
from .generic_lss import PENDING_STATUS, generic_estimate, generic_features, load_generic_model


def condition_differences(method):
    """List source-system differences without changing the submitted method."""
    from .retention_registry import curve_conditions

    reference = curve_conditions()
    differences = scope_mismatches(reference['scope'], method)
    if method.column.particle_um != reference['particle_um']:
        differences.append(f"particle_um: current {method.column.particle_um}; source {reference['particle_um']}")
    lower, upper = reference['phi_range']
    for index, node in enumerate(method.gradient):
        if not lower <= node.b_percent / 100 <= upper:
            differences.append(f'gradient[{index}].b_percent: current {node.b_percent}; source interval {lower * 100}–{upper * 100}')
    return differences


def estimate_retention(smiles, method):
    """Return A lookup, B domain-limited inference, or C generic regression."""
    from .prediction import infer, load_model
    from .retention_registry import measured_curves

    if method.mode != 'RP':
        raise ValueError('Retention estimation supports RP mode only')
    features = generic_features(smiles)
    features['descriptors'] = {
        'mw': features['mw'], 'clogp': features['crippen_logp'],
        'tpsa': features['tpsa'], 'hbd': features['hbd'],
        'aromatic_rings': features['aromatic_rings'], 'formal_charge': features['formal_charge'],
    }
    differences = condition_differences(method)
    model = load_model('lss-parameters')
    metadata = model['metadata']
    result = {
        'logkw': None, 's': None, 'tier': None, 'tier_label': None,
        'features': features, 'condition_differences': differences,
        'warnings': ['Condition difference / extrapolation: ' + item for item in differences],
        'validation_status': PENDING_STATUS,
        'scope': {key: value for key, value in metadata['scope'].items() if key != 'mode'},
        'phi_range': metadata['phi_range'], 'particle_um': 3.5,
        'license': 'CC BY-NC-SA 3.0 US',
        'reference': metadata['original_dataset_source'],
        'output_type': 'lss_parameters',
    }
    known = next((row for row in measured_curves() if row['smiles'] == features['canonical_smiles']), None)
    if known is not None:
        result.update(
            logkw=float(known['logkw']), s=float(known['s']), tier='A',
            tier_label='Measured curve', parameter_source=known['parameter_source'],
            model_version='retention-curves/' + metadata['model_version'],
            model_id='retention-curves', status='Literature-derived',
            observations=known['observations'],
        )
        result['warnings'].append('Parameters are LSS fits of the stored measured isocratic curves, not measurements in the current method.')
    else:
        try:
            predicted = infer('lss-parameters', smiles)
        except ValueError:
            predicted = None
        if predicted is not None:
            result['applicability'] = predicted['applicability']
        if predicted is not None and predicted['prediction'] is not None:
            logkw, strength = predicted['prediction']
            if np.isfinite([logkw, strength]).all() and -3 <= logkw <= 12 and 0 <= strength <= 30:
                result.update(
                    logkw=float(logkw), s=float(strength), tier='B',
                    tier_label='Scoped QSRR', parameter_source='Existing lss-parameters QSRR inference',
                    model_version=metadata['model_version'], model_id='lss-parameters',
                    status='Experimental model prediction',
                )
        if result['tier'] is None:
            logkw, strength, notices = generic_estimate(features)
            generic = load_generic_model()
            result.update(
                logkw=logkw, s=strength, tier='C', tier_label='Generic C18 estimate',
                parameter_source='Generic C18 constrained logk(0.35) and linear S regression from repository curves',
                model_version=generic['model_version'], model_id='generic-lss', status='Screening only',
            )
            result['warnings'].extend(notices + [
                '參數由通用回歸估算，非實測。',
                '訓練資料僅 ACN／Eclipse Plus C18／35 °C／0.1% 甲酸／φ 0.2–0.5；其他條件為外推。',
                '未考慮 pKa／離子化；未計算電離分布或 logD。',
            ])
            if method.mobile.b == 'MeOH':
                result['warnings'].append('係數由 ACN 資料擬合，MeOH 為外推。')
    if features['formal_charge'] != 0 or features['ionizable_groups']:
        result['warnings'].append('結構含電荷或可離子化基團；未建立 pKa、pH 電離分布與 logD 修正。')
    result['warnings'].append(PENDING_STATUS)
    fractions = np.linspace(*result['phi_range'], 31)
    result['curve'] = {
        'phi': fractions.tolist(),
        'k': (10 ** (result['logkw'] - result['s'] * fractions)).tolist(),
        'logk': (result['logkw'] - result['s'] * fractions).tolist(),
        'logarithm_base': 10,
    }
    return result


def parameter_tier(compound):
    """Keep calibration and explicit manual values ahead of estimated tiers."""
    if compound.parameter_origin == 'calibration':
        return 'D'
    if compound.parameter_tier is not None:
        return compound.parameter_tier
    if compound.parameter_origin == 'manual':
        return 'M'
    return 'A' if compound.parameter_origin == 'literature' else 'B'


def apply_estimate(compound, result):
    """Bind an estimate and all source information to the same compound ID."""
    from .schemas import Scope

    provenance = {
        key: result[key] for key in [
            'model_id', 'model_version', 'parameter_source', 'license', 'reference',
            'scope', 'phi_range', 'particle_um', 'validation_status', 'warnings',
            'condition_differences', 'features', 'tier',
        ]
    }
    provenance['canonical_smiles'] = result['features']['canonical_smiles']
    provenance['source'] = result['parameter_source']
    if 'applicability' in result:
        provenance['applicability'] = result['applicability']
    source = {'A': 'literature_derived', 'B': 'experimental_model_prediction', 'C': 'screening_only'}[result['tier']]
    return compound.model_copy(update={
        'logkw': result['logkw'], 's': result['s'], 'parameter_tier': result['tier'],
        'scope': Scope(**result['scope']), 'source': source,
        'parameter_origin': 'literature' if result['tier'] == 'A' else 'prediction',
        'retention_provenance': provenance,
    })
