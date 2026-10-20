"""RDKit only provides structure descriptors, never fabricated retention parameters."""
import csv,io,uuid
from .schemas import Compound
from .features import molecular_features
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors, Draw
NAMES={'caffeine':'Cn1c(=O)c2c(ncn2C)n(C)c1=O','acetaminophen':'CC(=O)Nc1ccc(O)cc1','aspirin':'CC(=O)Oc1ccccc1C(=O)O','benzene':'c1ccccc1','ethanol':'CCO','咖啡因':'Cn1c(=O)c2c(ncn2C)n(C)c1=O'}

def describe(smiles=None,name=None,molblock=None):
 resolved=smiles or NAMES.get((name or '').strip().lower())
 mol=Chem.MolFromMolBlock(molblock) if molblock else Chem.MolFromSmiles(resolved or '')
 if mol is None or mol.GetNumAtoms()==0:raise ValueError('Invalid structure / unknown local name; enter SMILES or MOL. No external lookup is required')
 if mol.GetNumAtoms()>300:raise ValueError('Small-molecule descriptor limit: 300 atoms')
 return {'name':name,'smiles':Chem.MolToSmiles(mol),'formula':rdMolDescriptors.CalcMolFormula(mol),'mw':Descriptors.MolWt(mol),'logp':Crippen.MolLogP(mol),'tpsa':rdMolDescriptors.CalcTPSA(mol),'hbd':rdMolDescriptors.CalcNumHBD(mol),'hba':rdMolDescriptors.CalcNumHBA(mol),'svg':Draw.MolsToGridImage([mol],molsPerRow=1,subImgSize=(250,180),useSVG=True),'retention_parameters':None,'prediction_status':'Descriptors are not logKw/S; scoped Rt inference is available in Retention Prediction','source':'RDKit descriptors; not retention prediction',**molecular_features(Chem.MolToSmiles(mol))[0]}

def import_file(content, filename):
    """Parse the existing formats; unnamed records receive names in the project."""
    suffix = filename.rsplit(".", 1)[-1].lower()
    rows = []
    if suffix == "csv":
        for index, row in enumerate(csv.DictReader(io.StringIO(content))):
            if index >= 20:
                raise ValueError("At most 20 compounds per import")
            name = row.get("name", "")
            smiles = row.get("smiles") or None
            descriptors = describe(smiles, name) if smiles else None
            rows.append({
                "id": str(uuid.uuid4()),
                "name": name,
                "kind": "small_molecule" if smiles else "parameterized",
                "smiles": descriptors["smiles"] if descriptors else None,
                "logkw": float(row["logkw"]) if row.get("logkw") else None,
                "s": float(row["s"]) if row.get("s") else None,
                "source": "model_based",
                "amplitude": 1,
                "descriptors": descriptors,
            })
    elif suffix in ["mol", "sdf"]:
        supplier = [Chem.MolFromMolBlock(content)] if suffix == "mol" else Chem.ForwardSDMolSupplier(
            io.BytesIO(content.encode()), removeHs=True,
        )
        for index, molecule in enumerate(supplier):
            if index >= 20:
                raise ValueError("At most 20 compounds per import")
            if molecule is None:
                raise ValueError("Invalid MOL / SDF record")
            name = molecule.GetProp("_Name") if molecule.HasProp("_Name") else ""
            smiles = Chem.MolToSmiles(molecule)
            descriptors = describe(smiles, name)
            rows.append({
                "id": str(uuid.uuid4()),
                "name": name,
                "kind": "small_molecule",
                "smiles": smiles,
                "logkw": None,
                "s": None,
                "source": "insufficient_data",
                "amplitude": 1,
                "descriptors": descriptors,
            })
    else:
        raise ValueError("Only CSV, SDF, MOL are supported")
    if suffix == "csv":
        raw_rows = list(csv.DictReader(io.StringIO(content)))
        for compound, raw in zip(rows, raw_rows):
            for key in ["mixture_parts", "concentration", "response_factor"]:
                if raw.get(key):
                    compound[key] = float(raw[key])
            if raw.get("concentration_unit"):
                compound["concentration_unit"] = raw["concentration_unit"]
    for row in rows:
        Compound.model_validate({key: value for key, value in row.items() if key != "descriptors"})
    if not rows:
        raise ValueError("No records")
    return rows
