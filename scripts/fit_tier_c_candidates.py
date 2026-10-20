"""Fit preregistered C1-C4 using repository curves; do not change serving files."""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold
from scipy.optimize import lsq_linear

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from elusim.engine import simulate
from elusim.estimation import estimate_retention
from elusim.generic_lss import FEATURE_NAMES, generic_estimate, generic_features
from elusim.schemas import Simulation

MOLECULES = [
    ("caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"),
    ("phenol", "Oc1ccccc1"),
    ("benzene", "c1ccccc1"),
    ("toluene", "Cc1ccccc1"),
    ("ethylbenzene", "CCc1ccccc1"),
    ("propylbenzene", "CCCc1ccccc1"),
    ("benzyl_alcohol", "OCc1ccccc1"),
    ("aniline", "Nc1ccccc1"),
    ("naphthalene", "c1ccc2ccccc2c1"),
    ("PGMEA", "COCC(C)OC(C)=O"),
    ("benzyl_acetate", "CC(=O)OCc1ccccc1"),
]
EXTRA_NAMES = ["aromatic_atom_fraction", "rotatable_bonds"]


def features_for(smiles):
    """Compute only the five existing and two preregistered extra features."""
    features = generic_features(smiles)
    molecule = Chem.MolFromSmiles(smiles)
    features["aromatic_atom_fraction"] = (
        sum(atom.GetIsAromatic() for atom in molecule.GetAtoms())
        / molecule.GetNumHeavyAtoms()
    )
    features["rotatable_bonds"] = rdMolDescriptors.CalcNumRotatableBonds(molecule)
    return features


def fit_equation(matrix, target, mask, alpha=0.0):
    """Fit a free intercept and bounded slopes with train-only scaling."""
    mean = matrix[mask].mean(axis=0)
    scale = matrix[mask].std(axis=0)
    scale[scale == 0] = 1.0
    design = np.column_stack([np.ones(len(matrix)), (matrix - mean) / scale])
    lower = np.full(design.shape[1], -np.inf)
    upper = np.full(design.shape[1], np.inf)
    lower[1] = 0.0
    upper[2:4] = 0.0
    fit_design = design[mask]
    fit_target = target[mask]
    if alpha:
        penalty = np.eye(design.shape[1])[1:] * np.sqrt(alpha)
        fit_design = np.vstack([fit_design, penalty])
        fit_target = np.concatenate([fit_target, np.zeros(len(penalty))])
    result = lsq_linear(fit_design, fit_target, bounds=(lower, upper), tol=1e-12)
    if not result.success:
        raise RuntimeError(result.message)
    return {
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "coefficients": result.x.tolist(),
        "alpha": alpha,
    }


def equation_predict(equation, matrix):
    """Evaluate the stored standardized linear equation."""
    standardized = (matrix - equation["mean"]) / equation["scale"]
    coefficients = np.asarray(equation["coefficients"])
    return coefficients[0] + standardized @ coefficients[1:]


def parameters(candidate, features):
    """Invert logk35=logKw-0.35*S with S=a*logKw+b.

    Substitution gives logKw=(logk35+0.35*b)/(1-0.35*a).
    S uses observed logKw and S in outer training groups only.
    """
    matrix = np.asarray(
        [[row[name] for name in candidate["feature_names"]] for row in features]
    )
    target = equation_predict(candidate["equation"], matrix)
    intercept, slope = candidate["s_coefficients"]
    if candidate["target"] == "logk35":
        denominator = 1.0 - 0.35 * slope
        if abs(denominator) < 1e-10:
            raise ValueError("S relation cannot be inverted")
        logkw = (target + 0.35 * intercept) / denominator
    else:
        logkw = target
    return logkw, intercept + slope * logkw


def default_method(compounds):
    """Use website demo geometry and the 5-to-95 percent, 10+5 min program."""
    return Simulation.model_validate(
        {
            "compounds": compounds,
            "gradient": [
                {"time_min": 0, "b_percent": 5},
                {"time_min": 10, "b_percent": 95},
                {"time_min": 15, "b_percent": 95},
            ],
        }
    )


def simulation_rows(logkw, strength, tiers):
    """Run the existing solver on the eleven specified structures."""
    rows = []
    for (name, smiles), value, slope, tier in zip(MOLECULES, logkw, strength, tiers):
        row = {
            "name": name,
            "smiles": smiles,
            "logkw": float(value),
            "s": float(slope),
            "tier": tier,
            "rt_min": None,
            "sigma_min": None,
            "eluted": False,
        }
        if np.isfinite([value, slope]).all() and -3 <= value <= 12 and 0 <= slope <= 30:
            method = default_method(
                [
                    {
                        "id": name,
                        "name": name,
                        "smiles": smiles,
                        "logkw": float(value),
                        "s": float(slope),
                    }
                ]
            )
            peak = simulate(method)["peaks"][0]
            row.update(
                rt_min=peak["rt_min"],
                sigma_min=peak.get("sigma_min"),
                eluted=bool(peak["eluted"]),
            )
        rows.append(row)
    return rows


def gate_rows(rows):
    """Evaluate the fixed ordering, resolution, range and elution gates."""
    by_name = {row["name"]: row for row in rows}
    gates = []
    chains = {
        "polarity": ["caffeine", "phenol", "benzene"],
        "homologues": ["benzene", "toluene", "ethylbenzene", "propylbenzene"],
        "benzyl_alcohol_toluene": ["benzyl_alcohol", "toluene"],
        "aniline_benzene": ["aniline", "benzene"],
        "ring_count": ["benzene", "naphthalene"],
        "esters": ["PGMEA", "benzyl_acetate"],
    }
    for name, chain in chains.items():
        times = [by_name[item]["rt_min"] for item in chain]
        passed = all(value is not None for value in times)
        passed = passed and all(left < right for left, right in zip(times, times[1:]))
        gates.append(
            {"gate": name, "passed": bool(passed), "values": dict(zip(chain, times))}
        )
    for left, right in [("phenol", "benzene"), ("benzene", "toluene")]:
        first, second = by_name[left], by_name[right]
        resolution = None
        if first["eluted"] and second["eluted"]:
            resolution = abs(second["rt_min"] - first["rt_min"]) / (
                2 * (first["sigma_min"] + second["sigma_min"])
            )
        gates.append(
            {
                "gate": f"rs_{left}_{right}",
                "passed": resolution is not None and resolution >= 1.0,
                "values": {"rs": resolution},
            }
        )
    for row in rows:
        gates.append(
            {
                "gate": f"range_and_elution_{row['name']}",
                "passed": bool(
                    -1 <= row["logkw"] <= 6 and 1 <= row["s"] <= 10 and row["eluted"]
                ),
                "values": {key: row[key] for key in ["logkw", "s", "rt_min", "eluted"]},
            }
        )
    return gates


def write_csv(path, rows):
    """Write nested values as JSON within ordinary CSV cells."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        json.dumps(value, ensure_ascii=False)
                        if isinstance(value, (list, dict))
                        else value
                    )
                    for key, value in row.items()
                }
            )


def run(write_model=False):
    """Fit C1-C4, record gates, and leave serving artifacts unchanged."""
    rows = json.loads((ROOT / "data/retention/curves.json").read_text(encoding="utf-8"))
    features = [features_for(row["smiles"]) for row in rows]
    scaffolds = np.array(
        [
            MurckoScaffold.MurckoScaffoldSmiles(
                mol=Chem.MolFromSmiles(row["canonical_smiles"])
            )
            or "<acyclic>"
            for row in features
        ]
    )
    groups = np.array(sorted(set(scaffolds)))
    np.random.default_rng(42).shuffle(groups)
    test_count = max(1, int(np.ceil(len(groups) * 0.2)))
    test_groups = set(groups[:test_count])
    test = np.array([group in test_groups for group in scaffolds])
    train = ~test
    inner_groups = np.array(sorted(set(scaffolds[train])))
    np.random.default_rng(42).shuffle(inner_groups)
    tuning_groups = set(inner_groups[: max(1, int(np.ceil(len(inner_groups) * 0.2)))])
    tuning = train & np.array([group in tuning_groups for group in scaffolds])
    inner_train = train & ~tuning
    assert not set(scaffolds[train]) & set(scaffolds[test])
    logkw = np.array([row["logkw"] for row in rows])
    strength = np.array([row["s"] for row in rows])
    logk35 = logkw - 0.35 * strength
    s_coefficients = np.linalg.lstsq(
        np.column_stack([np.ones(train.sum()), logkw[train]]),
        strength[train],
        rcond=None,
    )[0].tolist()
    molecules = [features_for(smiles) for _, smiles in MOLECULES]
    candidates = []
    all_gates = []
    molecule_rows = []
    for name in ["C1", "C2", "C3", "C4"]:
        names = FEATURE_NAMES + (EXTRA_NAMES if name in ["C3", "C4"] else [])
        matrix = np.array([[item[key] for key in names] for item in features])
        target = logkw if name == "C1" else logk35
        alpha = 0.0
        tuning_scores = {}
        if name == "C4":
            for value in [0.1, 1.0, 10.0]:
                equation = fit_equation(matrix, target, inner_train, value)
                predicted = equation_predict(equation, matrix[tuning])
                tuning_scores[str(value)] = float(
                    np.mean(np.abs(predicted - target[tuning]))
                )
            alpha = min([0.1, 1.0, 10.0], key=lambda value: tuning_scores[str(value)])
        candidate = {
            "candidate": name,
            "target": "logkw" if name == "C1" else "logk35",
            "feature_names": names,
            "equation": fit_equation(matrix, target, train, alpha),
            "s_coefficients": s_coefficients,
            "tuning_mae": tuning_scores,
        }
        fitted_logkw, fitted_s = parameters(candidate, features)
        residual = fitted_logkw[test] - 0.35 * fitted_s[test] - logk35[test]
        candidate["test_logk35_mae"] = float(np.mean(np.abs(residual)))
        candidate["test_logk35_rmse"] = float(np.sqrt(np.mean(residual**2)))
        values, slopes = parameters(candidate, molecules)
        results = simulation_rows(values, slopes, ["C"] * len(MOLECULES))
        gates = gate_rows(results)
        candidate["all_gates_pass"] = all(gate["passed"] for gate in gates)
        candidate["gates"] = gates
        candidates.append(candidate)
        for gate in gates:
            all_gates.append(
                {
                    "candidate": name,
                    **gate,
                    "test_logk35_mae": candidate["test_logk35_mae"],
                }
            )
        molecule_rows.extend({"model": name, **row} for row in results)
    old_path = ROOT / "backend/models/generic-lss-v1.json"
    if not old_path.exists():
        old_path = ROOT / "backend/models/generic-lss.json"
    old_model = json.loads(old_path.read_text(encoding="utf-8"))
    old = []
    for _, smiles in MOLECULES:
        feature = features_for(smiles)
        vector = np.array([feature[key] for key in old_model["feature_names"]])
        standardized = (vector - old_model["standardization"]["mean"]) / old_model[
            "standardization"
        ]["scale"]
        value = old_model["logkw"]["intercept"] + np.dot(
            old_model["logkw"]["coefficients"], standardized
        )
        slope = (
            old_model["s"]["intercept"] + old_model["s"]["logkw_coefficient"] * value
        )
        old.append((float(np.clip(value, -3, 12)), float(np.clip(slope, 0, 30))))
    molecule_rows.extend(
        {"model": "existing-v1", **row}
        for row in simulation_rows(
            [row[0] for row in old],
            [row[1] for row in old],
            ["C"] * len(old),
        )
    )
    method = default_method([{"id": "input", "name": "input", "logkw": 2, "s": 4}])
    complete = [estimate_retention(smiles, method) for _, smiles in MOLECULES]
    complete_rows = simulation_rows(
        [row["logkw"] for row in complete],
        [row["s"] for row in complete],
        [row["tier"] for row in complete],
    )
    molecule_rows.extend({"model": "existing-ABC", **row} for row in complete_rows)
    passing = [candidate for candidate in candidates if candidate["all_gates_pass"]]
    selected = (
        min(passing, key=lambda candidate: candidate["test_logk35_mae"])
        if passing
        else None
    )
    report = {
        "seed": 42,
        "rows": len(rows),
        "train_rows": int(train.sum()),
        "test_rows": int(test.sum()),
        "inner_train_rows": int(inner_train.sum()),
        "tuning_rows": int(tuning.sum()),
        "test_scaffolds": sorted(test_groups),
        "tuning_scaffolds": sorted(tuning_groups),
        "selected": selected["candidate"] if selected else None,
        "candidates": candidates,
        "existing_ABC_gates": gate_rows(complete_rows),
        "existing_ABC_molecules": complete_rows,
        "data_license": "CC BY-NC-SA 3.0 US",
        "data_source": "data/retention/curves.json",
        "serving_model_write_requested": write_model,
    }
    output = ROOT / "review/phase2.1"
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "tier-c-candidates.csv", all_gates)
    write_csv(output / "tier-c-sanity-molecules.csv", molecule_rows)
    (output / "tier-c-candidate-details.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if write_model:
        if selected is None:
            raise RuntimeError("No candidate clears all gates; serving files unchanged")
        write_selected(selected, rows, features, scaffolds, test)
    print(
        json.dumps(
            {
                "selected": report["selected"],
                "candidates": [
                    {
                        "candidate": item["candidate"],
                        "all_gates_pass": item["all_gates_pass"],
                        "test_logk35_mae": item["test_logk35_mae"],
                        "failed_gates": [
                            gate["gate"] for gate in item["gates"] if not gate["passed"]
                        ],
                        "coefficients": item["equation"]["coefficients"],
                    }
                    for item in candidates
                ],
            },
            indent=2,
        )
    )


def write_selected(selected, rows, features, scaffolds, test):
    """Store the selected equation, retaining the complete version-one file."""
    from elusim.generic_lss import PENDING_STATUS

    path = ROOT / "backend/models/generic-lss.json"
    previous = json.loads(path.read_text(encoding="utf-8"))
    backup = path.with_name("generic-lss-v1.json")
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    equation = selected["equation"]
    intercept, slope = selected["s_coefficients"]
    denominator = 1 - 0.35 * slope
    coefficients = np.asarray(equation["coefficients"])
    converted = coefficients / denominator
    converted[0] += 0.35 * intercept / denominator
    model = {
        **previous,
        "model_version": "2.0.0",
        "feature_version": "generic-c18-rdkit-five/2",
        "feature_names": selected["feature_names"],
        "validation_status": PENDING_STATUS,
        "standardization": {"mean": equation["mean"], "scale": equation["scale"]},
        "logkw": {
            "intercept": float(converted[0]),
            "coefficients": converted[1:].tolist(),
        },
        "s": {"intercept": intercept, "logkw_coefficient": slope},
        "fit_target": "log10(k) at phi=0.35",
        "target_equation": equation,
        "selected_candidate": selected["candidate"],
        "conversion": "logKw=(logk35+0.35*b)/(1-0.35*a); S=a*logKw+b",
        "application_notes": [
            "Constrained C18 regression; non-commercial use under the data license.",
            "Training input: ACN / Eclipse Plus C18 / 35 C / 0.1% formic acid / phi 0.2-0.5.",
            "Other conditions are extrapolation; no pKa or ionization correction.",
            "Candidate selection uses the preregistered gates followed by outer-test logk35 MAE.",
            "Outer-test results have participated in selection and are not untouched evidence.",
        ],
    }
    path.write_text(
        json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    fitted_kw, fitted_s = parameters(selected, features)
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    records = []
    for index, row in enumerate(rows):
        records.append(
            {
                "smiles": row["smiles"],
                "canonical_smiles": features[index]["canonical_smiles"],
                "scaffold": scaffolds[index],
                "split": "test" if test[index] else "train",
                **{key: features[index][key] for key in FEATURE_NAMES},
                "mw": features[index]["mw"],
                "logkw": row["logkw"],
                "s": row["s"],
                "logkw_fitted": fitted_kw[index],
                "s_fitted": fitted_s[index],
                "logkw_residual": fitted_kw[index] - row["logkw"],
                "s_residual": fitted_s[index] - row["s"],
            }
        )
    write_csv(output / "generic-lss-fit.csv", records)
    summary = {
        "seed": 42,
        "rows": len(rows),
        "train_rows": int((~test).sum()),
        "test_rows": int(test.sum()),
        "selected_candidate": selected["candidate"],
    }
    for name, mask in [("train", ~test), ("test", test)]:
        summary[name] = {}
        for target, actual, predicted in [
            ("logkw", np.array([row["logkw"] for row in rows]), fitted_kw),
            ("s", np.array([row["s"] for row in rows]), fitted_s),
            (
                "logk35",
                np.array([row["logkw"] - 0.35 * row["s"] for row in rows]),
                fitted_kw - 0.35 * fitted_s,
            ),
        ]:
            residual = predicted[mask] - actual[mask]
            summary[name][target] = {
                "mae": float(np.mean(np.abs(residual))),
                "rmse": float(np.sqrt(np.mean(residual**2))),
            }
    (output / "generic-lss-fit-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    review = ROOT / "review/phase2.1"
    for name in ["generic-lss-fit.csv", "generic-lss-fit-summary.json"]:
        (review / name).write_bytes((output / name).read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-model", action="store_true")
    arguments = parser.parse_args()
    run(write_model=arguments.write_model)
