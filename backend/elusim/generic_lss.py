"""Inspectable C18 regression, with no ionization or solvent correction."""
import functools
import json
import math
from pathlib import Path

import numpy as np
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

FEATURE_VERSION = 'generic-c18-rdkit-five/1'
FEATURE_NAMES = ['crippen_logp', 'tpsa', 'hbd', 'aromatic_rings', 'sqrt_mw']
PENDING_STATUS = 'unvalidated — pending user validation'
IONIZABLE_SMARTS = {
    'amine': '[NX3;!$(N-C=O)]',
    'aromatic_nitrogen': '[nH0]',
    'carboxylic_acid': 'C(=O)[O;H1,-1]',
    'phenol': '[OX2H]-c',
    'sulfonic_acid': 'S(=O)(=O)[O;H1,-1]',
    'phosphoric_acid': 'P(=O)([O;H1,-1])[O;H1,-1]',
}


def generic_features(smiles):
    """Parse a nonempty SMILES and compute the five regression features."""
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None or molecule.GetNumAtoms() == 0:
        raise ValueError('Invalid SMILES')
    molecular_weight = Descriptors.MolWt(molecule)
    ionizable_groups = [
        name for name, pattern in IONIZABLE_SMARTS.items()
        if molecule.HasSubstructMatch(Chem.MolFromSmarts(pattern))
    ]
    return {
        'canonical_smiles': Chem.MolToSmiles(molecule),
        'crippen_logp': Crippen.MolLogP(molecule),
        'tpsa': rdMolDescriptors.CalcTPSA(molecule),
        'hbd': rdMolDescriptors.CalcNumHBD(molecule),
        'aromatic_rings': rdMolDescriptors.CalcNumAromaticRings(molecule),
        'mw': molecular_weight,
        'sqrt_mw': math.sqrt(molecular_weight),
        'formal_charge': Chem.GetFormalCharge(molecule),
        'ionizable_groups': ionizable_groups,
        'feature_version': FEATURE_VERSION,
    }


@functools.lru_cache(maxsize=1)
def load_generic_model():
    """Load only the existing local JSON artifact, never executable weights."""
    path = Path(__file__).resolve().parents[1] / 'models/generic-lss.json'
    model = json.loads(path.read_text(encoding='utf8'))
    if model['feature_version'] != FEATURE_VERSION:
        raise ValueError('Generic LSS feature version mismatch')
    return model


def generic_estimate(features):
    """Evaluate standardized linear equations with explicit clipping notices."""
    model = load_generic_model()
    values = np.array([features[name] for name in FEATURE_NAMES], dtype=float)
    means = np.array(model['standardization']['mean'])
    scales = np.array(model['standardization']['scale'])
    warnings = []
    if not np.isfinite(values).all():
        values = np.where(np.isfinite(values), values, means)
        warnings.append('Nonfinite RDKit descriptor replaced by its training mean.')
    standardized = (values - means) / scales
    raw_logkw = float(model['logkw']['intercept'] + np.dot(model['logkw']['coefficients'], standardized))
    raw_s = float(model['s']['intercept'] + model['s']['logkw_coefficient'] * raw_logkw)
    logkw = float(np.clip(raw_logkw, -3, 12))
    strength = float(np.clip(raw_s, 0, 30))
    if logkw != raw_logkw:
        warnings.append(f'logKw clipped from {raw_logkw} to {logkw} within [-3, 12].')
    if strength != raw_s:
        warnings.append(f'S clipped from {raw_s} to {strength} within [0, 30].')
    return logkw, strength, warnings
