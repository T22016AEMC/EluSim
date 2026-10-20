"""Run only the preregistered C5-C7 candidate procedure, using local curves."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from rdkit import Chem
from scipy.optimize import lsq_linear

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
import fit_tier_c_candidates as previous
from elusim.generic_lss import generic_estimate, load_generic_model

EXTRA = {
    "C5": ["hetero_no"],
    "C6": ["aromatic_n", "carbonyl"],
    "C7": ["hetero_no", "aromatic_n", "carbonyl"],
}


def features(smiles):
    """Compute exactly the registered additional counts, without new descriptors."""
    result = previous.features_for(smiles)
    molecule = Chem.MolFromSmiles(smiles)
    result["hetero_no"] = sum(atom.GetAtomicNum() in (7, 8) for atom in molecule.GetAtoms())
    result["aromatic_n"] = sum(atom.GetAtomicNum() == 7 and atom.GetIsAromatic() for atom in molecule.GetAtoms())
    result["carbonyl"] = len(molecule.GetSubstructMatches(Chem.MolFromSmarts("[CX3]=[OX1]")))
    return result


def run(write_model=False):
    """Reuse the stored seed-42 scaffold partition and unchanged gates.

    S=a*logKw+b and logk35=logKw-0.35*S imply
    logKw=(logk35+0.35*b)/(1-0.35*a). Fit scalers and both equations
    only on outer training groups. No manual coefficient adjustment.
    """
    rows = json.loads((ROOT / "data/retention/curves.json").read_text(encoding="utf8"))
    model_path = ROOT / "backend/models/generic-lss-v2.json"
    if not model_path.exists():
        model_path = ROOT / "backend/models/generic-lss.json"
    model = json.loads(model_path.read_text(encoding="utf8"))
    vectors = [features(row["smiles"]) for row in rows]
    scaffold = np.array([
        previous.MurckoScaffold.MurckoScaffoldSmiles(mol=Chem.MolFromSmiles(row["canonical_smiles"])) or "<acyclic>"
        for row in vectors
    ])
    test = np.isin(scaffold, model["split"]["test_scaffolds"])
    train = ~test
    logkw = np.array([row["logkw"] for row in rows])
    strength = np.array([row["s"] for row in rows])
    target = logkw-.35*strength
    s_coefficients = np.linalg.lstsq(
        np.column_stack([np.ones(train.sum()), logkw[train]]), strength[train], rcond=None,
    )[0].tolist()
    molecules = [features(smiles) for _, smiles in previous.MOLECULES]
    old_estimates = []
    for row in molecules:
        vector = np.array([row[key] for key in model["feature_names"]])
        scaled = (vector-model["standardization"]["mean"])/model["standardization"]["scale"]
        value = float(model["logkw"]["intercept"]+np.dot(model["logkw"]["coefficients"],scaled))
        old_estimates.append((value, model["s"]["intercept"]+model["s"]["logkw_coefficient"]*value))
    old_rows = previous.simulation_rows(
        [row[0] for row in old_estimates], [row[1] for row in old_estimates], ["C"]*len(molecules),
    )
    old_range = np.ptp([row["rt_min"] for row in old_rows])
    reports = []
    molecule_rows = [{"model":"current_2.0.0", **row} for row in old_rows]
    candidates = []
    for name, extra in EXTRA.items():
        names = previous.FEATURE_NAMES+extra
        matrix = np.array([[row[key] for key in names] for row in vectors])
        mean = matrix[train].mean(axis=0)
        scale = matrix[train].std(axis=0)
        scale[scale == 0] = 1
        design = np.column_stack([np.ones(len(rows)), (matrix-mean)/scale])
        lower = np.full(design.shape[1], -np.inf)
        upper = np.full(design.shape[1], np.inf)
        lower[1] = 0
        upper[2:4] = 0
        upper[1+len(previous.FEATURE_NAMES):] = 0
        fit = lsq_linear(design[train], target[train], bounds=(lower, upper), tol=1e-12)
        if not fit.success:
            raise RuntimeError(fit.message)
        candidate = {
            "candidate":name, "target":"logk35", "feature_names":names,
            "s_coefficients":s_coefficients,
            "equation":{"mean":mean.tolist(),"scale":scale.tolist(),"coefficients":fit.x.tolist(),"alpha":0},
        }
        values, slopes = previous.parameters(candidate, molecules)
        result = previous.simulation_rows(values, slopes, ["C"]*len(molecules))
        gates = previous.gate_rows(result)
        times = [row["rt_min"] for row in result]
        span = float(np.ptp(times)) if all(value is not None for value in times) else None
        fitted_kw, fitted_s = previous.parameters(candidate, vectors)
        mae = float(np.mean(np.abs((fitted_kw-.35*fitted_s-target)[test])))
        candidate.update(
            all_gates_pass=all(row["passed"] for row in gates),
            rt_range_min=span, test_logk35_mae=mae,
            rt_range_increased=bool(span is not None and span > old_range),
        )
        for gate in gates:
            reports.append({
                "candidate":name, **gate, "test_logk35_mae":mae,
                "rt_range_min":span,"previous_rt_range_min":float(old_range),
                "rt_range_increased":candidate["rt_range_increased"],
                "coefficients":fit.x.tolist(),
            })
        candidates.append(candidate)
        molecule_rows.extend({"model":name, **row} for row in result)
    eligible = [row for row in candidates if row["all_gates_pass"] and row["rt_range_increased"]]
    selected = min(eligible, key=lambda row:row["test_logk35_mae"]) if eligible else None
    output = ROOT / "review/phase3a"
    output.mkdir(exist_ok=True, parents=True)
    previous.write_csv(output / "tier-c-candidates.csv", reports)
    previous.write_csv(output / "tier-c-sanity-molecules.csv", molecule_rows)
    details = {"selected":selected["candidate"] if selected else None, "previous_rt_range_min":float(old_range), "candidates":candidates}
    (output / "tier-c-candidate-details.json").write_text(json.dumps(details, indent=2)+chr(10),encoding="utf8")
    if write_model and selected:
        path = ROOT / "backend/models/generic-lss.json"
        backup = path.with_name("generic-lss-v2.json")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
        equation = selected["equation"]
        intercept, slope = selected["s_coefficients"]
        denominator = 1-.35*slope
        coefficients = np.asarray(equation["coefficients"])/denominator
        coefficients[0] += .35*intercept/denominator
        updated = {
            **model,
            "model_version":"3.0.0",
            "feature_version":"generic-c18-rdkit-carbonyl-aromatic-n/3",
            "feature_names":selected["feature_names"],
            "selected_candidate":selected["candidate"],
            "standardization":{"mean":equation["mean"],"scale":equation["scale"]},
            "target_equation":equation,
            "logkw":{"intercept":float(coefficients[0]),"coefficients":coefficients[1:].tolist()},
            "s":{"intercept":intercept,"logkw_coefficient":slope},
        }
        path.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+chr(10),encoding="utf8")
    # No serving change occurs when no registered candidate clears the rules.
    print(json.dumps(details, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-model", action="store_true")
    arguments = parser.parse_args()
    run(arguments.write_model)
