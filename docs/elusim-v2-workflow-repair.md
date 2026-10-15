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

## Release verification

Code commit: 631e575a542ebe70e45efabee5005fbeed9a129d; PR #4: https://github.com/T22016AEMC/EluSim/pull/4. Linux CI https://github.com/T22016AEMC/EluSim/actions/runs/38754523554 passed: backend 51 tests (8.67s), container 51 tests under 512 MiB (7.82s), frontend production build and container health.

Render deployment dep-db8ejegn74is73epmii0 reached live at 2026-10-15T14:58:08Z on the existing free service. Public health confirms the code commit. After the deployment-transition disconnect, the post-live repair smoke passed: legacy-source compounds produce Rt 5.621256 / 6.406693 / 7.031674 min and areas 0.5 / 0.3 / 0.2; a genuinely non-lookup QSRR input produces parameters and LSS Rt 7.212821 min. Invalid negative S still correctly returns detailed 422. No claim of experimental accuracy from these functional tests.

Public retention regression passed on commit 631e575: three experimental-curve components resolved; changing gradient time changed Rt from [2.781215, 1.293896, 5.407988] to [2.858424, 1.294723, 5.944867] min; changing parts preserved Rt while changing areas. Two optimization candidates were actually evaluated. Manual parameters survived resolve, and MeOH correctly caused abstention. Corresponding-source archive passed (229 files, 6,117,983 bytes), containing licenses, curve data and model weights, with no .env/.git/.venv paths.

## 操作驗收方式

1. 在 Retention Prediction 選 Load three experimental curve compounds，這是明確載入實驗曲線示範與相容條件的操作，不是未知化合物預測。
2. 在 Compounds 選 Resolve retention from structures；確認各 ID 的 logKw / S 與 Literature-derived 來源寫入。也可選 Structure workflow 後 Run simulation，成功解析的實際參數會回寫欄位。
3. 輸入任意非負份數，例如 5:3:2，按 Run simulation。第一張圖是實際計算的峰；Gradient Profile 預設收合。
4. 調整梯度後重新模擬，或至 Gradient Optimization 搜尋候選並套用。條件不相容時修正設定或使用適用的手動／校正參數，不能解除科學限制。
5. 使用新結構前，可在 LC Mode & Column 明確選 Use model-compatible conditions；模型仍可能因結構超出適用範圍而拒絕。

## Changed modules

Backend: chemistry.py (import IDs), conditions.py (mismatch details), engine.py (provenance/result states/resolved compounds), main.py (conditions route), prediction.py, retention_registry.py, schemas.py, new sources.py. Existing solver equations and mixture.py are unchanged.

Frontend: types.ts, main.tsx, RetentionWorkspace.tsx, Chart.tsx; new sources.ts, project.ts, api.ts, ModelConditions.tsx. Existing UVWorkspace and model files are unchanged. Tests: test_workflow_repair.py plus source-code assertions in existing tests, workflow-repair.spec.ts and result-title assertions in workbench.spec.ts. New public_repair_smoke.py and this report/evidence.

Operational limits remain unchanged: free Render instance, bounded computation slots and 30s worker timeout, upload/compound/optimization budgets. Heavy or concurrent workloads can be rejected or timed out rather than exhausting the service. No paid resource change was made. Physical-phone/cellular testing was not performed for this repair; automated Pixel 7 viewport testing is explicitly separate from the earlier user-reported basic V1 page usability.

Final public browser acceptance: **18/18 passed, 0 skipped, 0 failed, 0 flaky**, 720.41s, beginning 2026-10-15T15:01:46Z. Desktop Chromium 9/9 and Pixel 7 emulation 9/9 against https://elusim-v1.onrender.com; real API computation, not mocked responses. Includes original UV/DAD/retention/manual workflows and all new migration, chart-order, failure, model-conditions, non-elution and parameter-writeback cases. Public screenshots and JSON retained here. No physical device/cellular test was performed.

Release is operational at the original URL with code commit 631e575a542ebe70e45efabee5005fbeed9a129d. The subsequent documentation-only commit adds acceptance evidence and does not change the deployed application. Scientific limitations above remain unresolved by design; no broad QSRR accuracy or detector-specific quantitative signal claim is made.
