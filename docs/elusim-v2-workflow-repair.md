# EluSim V2 controlled workflow repair

Date: 2026-10-15 (Asia/Taipei). Base: 3673ccfa8943b154e9b219164458ce50d24d98d2. User confirmed that EluSim_V2 is the intended source when EluSim_V2(1) was not present. Local source, remote development branch and live Render deployment matched this commit. Branch: codex/v2-workflow-repair.

## Direct causes verified before repair

1. Compound.source accepted human-readable English Literal values while TypeScript allowed arbitrary string. Chinese 基於模型 and unknown legacy labels returned HTTP 422 at compounds[0/2].source on the live server. Evidence: v2-repair-evidence/baseline-422.json.
2. Startup and JSON import loaded raw localStorage data with no schema migration; invalid source values persisted on each save.
3. Chart.tsx always added Program %B and Inlet %B, even with zero analyte traces. Result presence alone controlled success-like rendering.
4. Failed simulation requests retained the last successful result; changed method settings could leave previous results visible.
5. Model conditions were available only through Retention Prediction, with generic mismatch messages. Default Generic C18 / 25°C / 5–95% B is incompatible with the retained curve model.
6. MOL/SDF import reused import-0 etc., unlike CSV UUIDs, allowing duplicate compound IDs across imports.

## Scope of repair

Stable source codes and separate display labels; conservative backend aliases plus frontend project-schema migration. Unknown text becomes unknown_legacy, with original source_legacy retained. The pre-migration project is saved under elusim-project-before-v2-migration. Valid compound IDs, SMILES, parameters, method, composition and descriptors remain; missing/duplicate IDs are repaired per record. Malformed project storage is retained and not silently overwritten. JSON project import also migrates. No automatic localStorage deletion.

Prediction and Compounds share IDs and data. Explicit resolve prioritizes measured curves then existing QSRR; successful values enter the unchanged migration solver, preserving manual parameters unless replacement is explicitly requested. Direct Structure-workflow simulation also returns and persists the actual resolved per-ID parameters used by the solver; this closes the path that otherwise left parameter fields empty after successful simulation. Source labels now cannot be translated into API values by UI translation. API error messages identify the compound, ID, field path and HTTP endpoint/status.

Model-compatible settings are explicitly available in the LC method workspace and existing prediction workspace. GET /api/retention/conditions reads the existing model scope/phi range and documented 3.5 µm material specification. The user must click to apply settings; mismatches list current and required values. No scientific boundaries were relaxed.

Main result is Simulated Chromatogram with compound traces, total signal, Rt markers, legend selection and relative-response axis. Gradient Profile is separate and collapsed by default, including programmed/inlet %B and dwell information. No valid traces means no chromatogram. Missing parameters, incompatible scope, invalid API input, missing efficiency/signal and physical non-elution are distinguished. Changed method or failed request hides the previous result; explicit overlay remains available after successful simulation.

Existing multi-component parts/concentration/response and area-to-height calculations remain; 5:3:2 normalizes automatically. No pressure, overload or detector-specific model was added. Optimization retains the original bounded candidate engine and now reports compound-specific eligibility blockers. UV/DAD and calibration remain intact.

## Scientific limits and licenses (unchanged)

Model lss-parameters 2.1.0 is experimental, not externally validated. Applicable only to Agilent Eclipse Plus C18 3.5 µm, 35°C, water / ACN with 0.100% formic acid in both phases, formulation-defined pH, 20–50% ACN. Matching conditions does not imply verified gradient accuracy. Exact experimental lookup is literature_derived; QSRR-only inference remains experimental_model_prediction. Direct method-specific Rt does not supply transferable logKw/S. Other modes/conditions abstain or require user-supplied parameters/calibration.

Original heldout log10(k) MAE 0.41469, RMSE 0.51220 and order agreement 0.57049 remain unchanged; independent gradient Rt error is unavailable. No new statistical accuracy claim. All three weights and datasets preserved; SHA256 in v2-repair-evidence/model-hashes.json. Application AGPL and independent model/data licenses retained, including previously authorized non-commercial CC BY-NC-SA 3.0 US data/weights.

## Validation

Baseline: 39 backend tests passed. Initial new tests found source_legacy:null prevented original-text retention; fixed before release. Final backend: 50 passed (88.89s), including effective-parameter replay through the same solver. Existing scientific assertions preserved; source-value assertions updated to stable machine codes. TypeScript and Vite production build passed. Existing large-bundle warning and Starlette testclient deprecation warning remain; no new runtime dependency added.

Initial desktop + Pixel 7 viewport regression: 16/16 passed. A final Structure-workflow response-to-parameter-state repair is additionally covered before deployment. Browser viewport tests are not physical-phone/cellular tests.

Commands:

    python -m pytest -q backend/tests --junitxml=artifacts/v2-repair-backend.xml
    cd frontend
    node node_modules/typescript/bin/tsc --noEmit
    node node_modules/vite/bin/vite.js build
    ELUSIM_BASE_URL=<tested origin> node node_modules/@playwright/test/cli.js test
    python scripts/public_repair_smoke.py https://elusim-v1.onrender.com --baseline
    python scripts/public_repair_smoke.py https://elusim-v1.onrender.com

Deployment retains Dockerfile, backend/requirements.in + requirements.lock, frontend lockfile, CI and existing Render service/URL. No Windows venv is part of the deployable project. Linux dependency installation and the 512 MiB Docker gate must pass before promoting production.

Additional non-database test: CC(=O)Nc1ccc(OCCC)cc1 is absent from the measured-curve registry and training set; the unchanged QSRR accepts its domain and predicts logKw 2.3092989204 / S 4.6164833713. Its parameters enter the real LSS solver. This is functional inference verification, not experimental accuracy validation. The additional test passed (1 passed, 11 deselected); full Linux CI will run all 51 tests.

Final local browser run: 17/18 passed; mobile optimization returned HTTP 504 while an additional Python test encountered Windows WMI/native resource errors. The unchanged test passed in isolation (38.0s whole workflow; 1/1), without raising the server 30s compute budget. All 18 cases have passed; this was not a single clean final suite run. Both original failure and isolated rerun JSON are retained. Linux CI and public-site validation remain release gates.
