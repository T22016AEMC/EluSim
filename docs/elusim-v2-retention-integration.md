# EluSim V2 retention integration (2026-10-14)

## Outcome and release gates

Incremental work on codex/v2-retention-integration from f86291c831eca228f82d5037950bb3062df293b8. Production at task start: b994d4406c1873d2373b19059e63bc5270a42d96, Render srv-db6s5n59fdbs73e5oj7g, https://elusim-v1.onrender.com/. The local baseline differs only in .gitattributes and acceptance/deployment documents, not application code. No main merge, replacement application, cloud service or formal URL change.

Local baseline: 30 tests passed. Final backend: 39 tests passed (all original 30 plus 9 integration tests). TypeScript passed; production Vite build passed with existing large-bundle warning. Final desktop/mobile-emulation, Linux CI/container and public deployment are release gates; final evidence appended after execution. One overloaded Windows attempt crashed in platform/WMI and another timed out; these are not reported as passing. CRLF-sensitive edits initially failed new Scope tests and were corrected before the 39-pass run. A coarse 60-minute plotting grid failed numerical peak integration; test uses a sufficiently sampled 20-minute window, without changing the peak-width model. Analytical area and finite-grid numerical area remain distinct.

## Changes and user workflow

- backend/elusim/conditions.py, retention_registry.py, retention_models.py: exact chemical scope, structure identity and measured-curve/QSRR distinction. Existing SciPy DOP853 solvent-front migration remains the solver; its RHS obtains k from the LSS adapter. Nonlinear families are not enabled without data/validation.
- schemas.py, engine.py, mixture.py, chemistry.py: component-owned parts/concentration/response/provenance, UUID imports, validated CSV fields, area rather than height scaling, scope guards for simulation and optimization.
- prediction.py and main.py: safe multioutput JSON model inference; curve prediction, compound resolution and read-only experimental database routes. Existing direct Rt and UV endpoints retained.
- frontend/src/main.tsx, types.ts, RetentionWorkspace.tsx: RDKit validation on addition, Compound ID selection, compatible predictions automatically populate Retention Parameters, manual values protected unless explicit replacement; mixture fields and batch parts editing; peak area/height exports. Existing UV/DAD workspace and responsive layout retained.
- scripts/build_retention_curves.py, train_scoped_retention.py, validate_scoped_retention.py: reproducible real-data curation, grouped ML comparison, heldout errors; other evidence scripts record read-only source/license checks.

Use Retention Prediction → Load scoped curve conditions (or three experimental curve compounds) → select a compound → Predict retention. An eligible logKw/S result updates that ID. In Compounds, Resolve retention from structures processes the mixture and preserves manual parameters by default. Then Run simulation / Optimize gradient use those same eligible parameters. Direct RepoRT Rt is displayed separately and never fills logKw/S. Invalid structure or out-of-domain input withholds prediction. Editing a predicted compound's SMILES invalidates its old parameters. Changing chemistry does not relabel incompatible predictions as transferable manual parameters.

## Real data and QSRR

Source: [Boswell isocratic retention database](https://www.retentionprediction.org/hplc/database/), curated [Wiczling isocratic-qsrr snapshot](https://github.com/wiczling/isocratic-qsrr/tree/2951822d97bd76eeeb244989c9e1691ca4a1ff88/data/deliv). Original site download returned HTTP 403 here; pinned author-curated observations/SMILES were used. Source web method/license independently read; original CSV not independently byte-matched. Ancillary pH.csv is retained as curator data and is not a validated ionization model.

Each original curve stays grouped by canonical structure. Four distinct measured compositions in 20–50% ACN are required. Fit log10(k) = logKw − S phi by existing identifiable least-squares module; reject nonphysical parameters, charged structures, fewer than four compositions or fit RMSE >0.1 log10(k). Threshold is a disclosed representation-quality filter, not proof of external predictive accuracy. Result: 273 curves / 272 distinct structures / 1,092 measured points. Raw measurements, excluded records, hashes and attribution retained in data/retention and docs/v2-evidence.

Model lss-parameters 2.1.0 uses existing RDKit 10 descriptors + Morgan radius2/256-bit fingerprints, no arbitrary logP multiplier, no pKa/logD approximation. Conditions are an exact scope gate (one system), not invented cross-column covariates. Ridge / Random Forest / multioutput Gradient Boosting compared; validation parameter RMSE selects Gradient Boosting. Same canonical compound and Murcko scaffold cannot span train/test. 155 train / 41 validation / 76 test structures; artifact not refit on test. Safe JSON parity checked against sklearn on heldout structures. Production requires only existing NumPy/RDKit/SciPy, no additional ML serving installation.

All-heldout parameter RMSE: GB 0.7406, RF 0.7661, Ridge 1.2284, mean baseline 1.0756 (combined logKw/S error, not Rt minutes). On actual heldout curve points: log10(k) MAE 0.41469 / RMSE 0.51220; k MAE 5.52595 / RMSE 13.19683; logKw MAE 0.50394; S MAE 0.68165. 308 points from 77 curves / 76 unique test structures (one duplicated canonical structure stays in the same group). Order agreement at phi=0.35 is 0.57049, excluding reference logk differences <=0.01. In-domain subset: 264 points / 66 curves / 65 structures, logk RMSE 0.50984 and order agreement 0.53948. These limitations travel with every model result. No confidence percentage or empirical Rt error interval is asserted.

Status: Experimental model prediction, suitable only as a cautious screening estimate requiring calibration/experimental confirmation. Exact measured-curve lookup is Literature-derived, with its own fit residual. This model is not a robust universal separation recommender. Independent laboratory, gradient Rt MAE/RMSE and cross-column/solvent validation remain unavailable.

## Enabled conditions and boundaries

Agilent Eclipse Plus C18, 3.5 µm, 35°C, A water +0.100% formic acid, B ACN with 0.100% formic acid, 20–50% ACN. pH control must be formulation-defined with numeric pH null: this does not assume a constant pH or calculate ionization. Other pH, buffer, temperature, particles, phase or solvent are rejected. Geometry scaling assumes equivalent packing phase ratio and user-provided void/efficiency; batch/pore selectivity is unverified. Pure-water logKw is extrapolated; prediction/simulation/optimization outside 20–50% ACN is withheld. No Rt-only model is transformed into two free LSS parameters.

Three real examples: anthranilic acid, caffeine, diethyl malonate, each with four independent measured compositions. The three-component UI fixture is experimental parameter data, while geometry/efficiency/run settings are simulation assumptions, not an experimental gradient validation run. Other LC modes remain unsupported quantitatively; manual known parameters and independent calibration are preserved.

## Mixture and signal semantics

Up to the existing 20-component budget. Parts 5:3:2 normalize to 0.5/0.3/0.2. Per-ID fields survive reorder/deletion. CSV accepts mixture_parts, concentration, concentration_unit (mM or mg/mL), response_factor; negative/nonfinite values and mixed concentration units rejected. UI batch parts editing binds values to the displayed component IDs at application time.

Parts mode assumes total concentration 1 relative amount/µL; it does not infer absolute concentration. Concentration mode: mM × injection µL = nmol; mg/mL × µL = µg. Injected amount × relative response gives ideal integrated area. Gaussian height = area/(sqrt(2π) sigma). Existing width model unchanged. Default equal relative response is illustrative, not calibrated UV absorbance. Legacy amplitude remains accepted for old project compatibility but is ignored; concentration-overload effects are not claimed. Ratio-only changes leave Rt unchanged, as verified. Exports include analytical area/height/amount units; coarse finite plotting grids may integrate inaccurately and are warned.

## License and deployment

Owner explicitly approved non-commercial service on 2026-10-14. Data/derived curves/lss-parameters weights retain CC BY-NC-SA 3.0 US, attribution, modification notice and share-alike. They are independent data artifacts, separately labeled from AGPL-3.0-or-later application code. Existing RepoRT CC BY-SA and UV CC BY terms unchanged. See data/retention/LICENSE.md, backend/models/README.md, NOTICE.md. Do not infer commercial permission from the curator repository's BSD code license. Commercialization requires replacing these data/weights or obtaining rights; licensing classification of novel combined/derivative uses may need legal review. AGPL corresponding source remains available through /api/source.

Five upstream repositories were re-read at unchanged pinned commits; core filenames/hashes, licenses and checkpoint inventory in docs/v2-evidence/retention-upstream-recheck.json. PyLSS is parameter-to-Rt, not structure-to-parameters; retained AGPL reference. GRIP still has no explicit license; no code or weights copied. TIMPANI and 2-step are method Rt/transfer approaches, not compatible off-the-shelf LSS curves; DeepLC is peptide-specific. No unverified upstream weight licensing is assumed. Existing detailed source reviews remain in docs/elusim-v2-model-review.md. The 2025 Kinetex supporting XLSX was discovered to be CC BY-NC despite CC BY article text; it was not used in the shipped model.

Reproduction:

    python scripts/fetch_isocratic_evidence.py
    python scripts/build_retention_curves.py
    python scripts/train_scoped_retention.py
    python scripts/validate_scoped_retention.py
    python -m pytest -q backend/tests
    cd frontend && pnpm build
    ELUSIM_BASE_URL=<target> pnpm test:e2e
    python scripts/public_smoke_retention.py https://elusim-v1.onrender.com

Use scripts/training-requirements.txt for offline training only; backend/requirements.lock for serving. Linux CI builds Docker and runs backend tests with 512 MiB. Free Render service and same URL retained; no paid resources requested. Mobile viewport simulation is distinct from physical-device/cellular testing; no new physical-device validation is claimed.
