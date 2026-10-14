"""Versioned bounded RDKit descriptors; no pKa or logD inference."""
import numpy as np
from rdkit import Chem,DataStructs
from rdkit.Chem import Descriptors,Crippen,rdMolDescriptors,rdFingerprintGenerator
VERSION='rdkit-morgan2-256-plus10/1'
NAMES=['mw','clogp','tpsa','hbd','hba','rotatable_bonds','aromatic_atoms','formal_charge','rings','heavy_atoms']
GEN=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=256)
PATTERNS={'aromatic_ring':'a1aaaaa1','alkene':'C=C','carbonyl':'C=O','nitro':'[N+](=O)[O-]','azo':'[N;X2]=[N;X2]','conjugated_diene':'C=C-C=C','amine':'[NX3;!$(N-C=O)]','carboxylic_acid':'C(=O)[OH]'}
def molecular_features(smiles):
 mol=Chem.MolFromSmiles(smiles)
 if mol is None or not 1<=mol.GetNumHeavyAtoms()<=300:raise ValueError('Invalid SMILES or 300-atom model limit')
 canonical=Chem.MolToSmiles(mol);fp=GEN.GetFingerprint(mol);bits=np.zeros(256,dtype=np.uint8);DataStructs.ConvertToNumpyArray(fp,bits)
 values=[Descriptors.MolWt(mol),Crippen.MolLogP(mol),rdMolDescriptors.CalcTPSA(mol),rdMolDescriptors.CalcNumHBD(mol),rdMolDescriptors.CalcNumHBA(mol),rdMolDescriptors.CalcNumRotatableBonds(mol),sum(a.GetIsAromatic() for a in mol.GetAtoms()),Chem.GetFormalCharge(mol),rdMolDescriptors.CalcNumRings(mol),mol.GetNumHeavyAtoms()]
 patterns={name:len(mol.GetSubstructMatches(Chem.MolFromSmarts(pattern))) for name,pattern in PATTERNS.items()}
 patterns['aromatic_ring']=rdMolDescriptors.CalcNumAromaticRings(mol)
 return {'canonical_smiles':canonical,'descriptors':dict(zip(NAMES,values)),'fingerprint':bits.tolist(),'substructures':patterns,'feature_version':VERSION,'ionization_warning':'Formal charge only; no validated pKa, microstate fractions or logD calculated'},np.r_[values,bits].astype(float)
