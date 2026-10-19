# Phase 1 implementation notes

Source: origin/codex/v2-workflow-repair at 12e3f74d9ce3718c74607353c4d0c7d0a9f7d626.
Working branch: codex/v3-p0-core-fixes. No branch merge, production-branch push, deployment-setting edit or deployment is part of this change.

## What changed

- The existing plug-flow ODE now exposes retention_state(): Rt, outlet phi, k_e, elution flow and local outlet slope. retention() retains its float-or-None interface for calibration callers.
- Column sigma uses G*t0_e*(1+k_e)/sqrt(N). Poppe is the default; band_compression=none sets G=1 but still uses outlet state. Injection and extra-column variance conventions are unchanged. Each peak includes k_e, phi_outlet, compression_factor, sigma_col_min and parameter_tier.
- The central-difference step is min(0.01*t0_e, 0.001 min). Offset one-sided samples select the post-event slope at a step or kink. Multiple segments use a local approximation. A singular local Poppe denominator falls back to G=1 with a warning; the corresponding experimental behavior remains for user review.
- Formula reference, without copying simulator source: Poppe, Paanakker & Bronckhorst, Journal of Chromatography 204 (1981), 77–84, https://doi.org/10.1016/S0021-9673(00)81641-6.
- POST /api/retention/estimate tries A stored measured-curve parameters, B the existing lss-parameters model within its structure domain, then C generic C18 regression. A/B method differences become warnings. Invalid SMILES and non-RP estimation requests return errors; existing request size/unit/entity constraints remain.
- Source, conditions, features, model version, tier and warnings are retained per Compound ID. All newly fitted/estimated outputs use validation_status: "unvalidated — pending user validation".
- Eligibility still blocks unsupported modes/entities, missing parameters and numeric bounds. Scope, solvent, temperature, particle, gradient-range and structure differences are warnings. An invalid edited structure cannot overwrite existing parameter values.
- Calibration is D and retains priority. Manual edits become M; background estimates cannot overwrite M/D. An explicit per-compound re-estimate can replace M. Re-estimate all processes A/B/C only.
- The frontend debounces structure/condition edits by 600 ms, discards obsolete responses and waits for estimates before simulation. Method templates remain explicit button actions. Diagram legends/tables include tiers, and C is marked 估算.
- Parameter and peak-table CSV exports contain the requested columns. Manual edits retain available structure features; editing a protected structure clears stale structure descriptors without changing its retention values. Missing descriptors are left blank rather than fabricated.
- The existing optimizer, UV/DAD and calibration workflows remain. The optimizer grid is unchanged; candidate-condition differences use the same warning policy.

## Regression artifacts

scripts/fit_generic_lss.py reads only data/retention/curves.json. It uses Ridge alpha=1 for standardized Crippen logP, TPSA, HBD, aromatic rings and sqrt(MW), followed by OLS S=c0+c1*logKw_fitted. No runtime dependency was added. NumPy and RDKit perform inference.

Murcko seed 42 assigns 118 scaffolds / 189 rows to training and 30 scaffolds / 84 rows to test. The complete acyclic group stays together. Standardization and both coefficient fits use training rows only. A separate S+sqrt(MW) calculation is written as numbers; it does not select a deployment equation using test rows. C output is clipped to logKw [-3,12] and S [0,30], with a clipping warning. Solvent, ionization and source-condition notices are explicit.

Artifacts:
- backend/models/generic-lss.json: equations, standardization, feature version, source hash, conditions, license, pending-user status.
- artifacts/generic-lss-fit.csv: each structure/curve, scaffold split, features, target values, fits and residuals.
- artifacts/generic-lss-fit-summary.json: numeric summary only.
- artifacts/gradient-analytic-comparison.json: synthetic equation comparisons below.

Existing curve/weight files are preserved. The new coefficients retain the source data's CC BY-NC-SA 3.0 US license and attribution. No external dataset or incompatible simulator source was downloaded or copied.

## How software was checked

Baseline: pytest -q reported 51 passing tests. Final Python run: 67 passed, 0 failed (64.33 s), with the existing Starlette test-client deprecation notice. The nine targeted equation/isocratic checks also passed. pnpm build completed; the existing large-bundle notice remains.

Commands (run from repository root unless noted):

    python scripts/fit_generic_lss.py
    python -m pytest -q backend/tests/test_gradient_analytic.py backend/tests/test_engine.py::test_isocratic_analytic_and_zero_slope
    python -m pytest -q --junitxml=artifacts/v3-p0-pytest.xml
    cd frontend
    pnpm build
    ELUSIM_BASE_URL=http://127.0.0.1:8110 pnpm test:e2e

Python test modules added: test_gradient_analytic.py and test_estimation.py. Existing test_engine.py, test_retention_integration.py, test_workflow_repair.py and test_v2_prediction.py change old condition-rejection assertions to warning/parameter-priority checks; commit message lists each test and reason. The direct-Rt adapter fixture now checks actual parameter flow instead of an obsolete scope gate.

Playwright added: p0-estimation.spec.ts, covering default-method SMILES input, a non-database structure, generic C, debounce, parameter/peak CSV, method refresh, M/D priority and a delayed real-response race. Existing retention-integration.spec.ts and workflow-repair.spec.ts now expect automatic population and warning-only transfer. The old direct-Rt UI test explicitly re-selects its method-specific model after tab remount, so its exact-method gate is still exercised.

Initial UI test failures were a select locator and an old test returning to the default model after tab remount. Neither was resolved by extending timeouts or relaxing numerical assertions. No experimental data check or scientific conclusion is implied by software-test results.

### Synthetic equation comparisons

All cases use vm=0.3 mL, F=0.3 mL/min, N=12000, zero injection variance and zero extra-column variance. Early-isocratic and zero-S cases use the corresponding limits of the supplied equation.

| case | logKw | S | φ0→φ1 | tG min | dwell mL | tR formula/program min | relative difference | sigma_col formula/program min | relative difference |
|---|---:|---:|---|---:|---:|---|---:|---|---:|
| zero_dwell | 2 | 4 | 0.1→0.5 | 10 | 0 | 8.46862863472 / 8.46862863472 | 2.2204e-16 | 0.0281608021296 / 0.0281608021296 | 4.1744e-14 |
| with_dwell | 2.5 | 5 | 0.1→0.6 | 8 | 0.12 | 7.35629751857 / 7.35629751686 | 2.3274e-10 | 0.0173752268785 / 0.0173752268909 | 7.1345e-10 |
| short_gradient | 3 | 6 | 0.05→0.8 | 5 | 0.3 | 5.35112175481 / 5.35112175545 | 1.1887e-10 | 0.00935402059630 / 0.00935402059228 | 4.2939e-10 |
| long_gradient | 1.5 | 3 | 0.2→0.5 | 20 | 0.6 | 7.63096166773 / 7.63096155684 | 1.4532e-8 | 0.0517459735203 / 0.0517459740144 | 9.5479e-9 |
| early_isocratic | -0.5 | 2 | 0.1→0.5 | 10 | 1.2 | 1.19952623150 / 1.19952623150 | 3.3307e-16 | 0.0109501262552 / 0.0109501262552 | 0.0000e+0 |
| zero_s | 1 | 0 | 0.1→0.6 | 10 | 0 | 11.0000000000 / 11.0000000000 | 1.5543e-15 | 0.100415802209 / 0.100415802209 | 0.0000e+0 |

## Pending user checks

| Item for user experimental/data checks | Files / outputs |
|---|---|
| Gradient width equation, k_e and compression behavior under actual instrument conditions | backend/elusim/engine.py; peak-table CSV; artifacts/gradient-analytic-comparison.json |
| Multi-segment gradients, steps, local slope and variable-flow approximation | backend/elusim/engine.py: outlet_slope, retention_state, band_width |
| Curve identity, original isocratic observations and fitted LSS interpretation | unchanged data/retention/curves.json; backend/elusim/estimation.py tier A |
| Existing QSRR outputs and structure-domain rules | unchanged backend/models/lss-parameters.json.gz; backend/elusim/prediction.py; parameter CSV |
| Generic coefficients, scaffold split, residuals and optional S+sqrt(MW) choice | scripts/fit_generic_lss.py; backend/models/generic-lss.json; artifacts/generic-lss-fit.csv; artifacts/generic-lss-fit-summary.json |
| Transfer to other stationary phases, MeOH, temperatures, pH/formulations and phi ranges | estimate condition_differences/warnings; peak warnings; parameter CSV |
| Ionizable/charged structures, salts and absence of pKa/logD correction | backend/elusim/generic_lss.py; tier C warnings |
| Clipping, extrapolation and resulting elution/non-elution | backend/elusim/generic_lss.py; exported peak table |
| Experimental calibration inputs, fitted parameters and source conditions | existing Experimental Calibration workspace; tier D records |
| Experimental Rt, peak width, Rs, detector response and mixture-signal interpretation | peak-table CSV, existing simulation JSON and trace CSV |

## Limits

No scientific conclusion is made from these software checks or fit outputs. Data/model transfer, coefficients, widths and experiment interpretation remain pending user work. C provides numerical estimates rather than compound-specific measurements. Finite run windows can still give non-elution; insufficient efficiency or unsupported entities do not acquire invented peaks. The existing Gaussian/relative-response assumptions remain, with no new tailing, overload, pressure, van Deemter, nonlinear retention or detector model. No deployment or production-site test is performed in this phase.

The M/D preservation checks also cover partially empty records: absent S is not silently estimated. Explicit replacement can fill M, while D remains protected. Existing scientific source codes are retained for migration; the legacy status label is displayed neutrally as pending user review.

Final local browser run: 24 passed, 0 failed, 0 skipped, 0 flaky; desktop 12 and Pixel 7 viewport 12. Duration 579.54 s. Results: artifacts/v3-p0-browser-tests.json. Tests used production bundle index-C32UmUCI.js; final comment/format cleanup produces the same bundle. This is browser emulation only, without a physical-phone or public-site test.

The first full UI run reported 22 passing and 2 failing cases because the old direct-Rt test returned to default auto mode after a tab remount. Explicit model selection fixed that test; the final complete run above includes both viewports. The initial standalone select-locator issue was corrected using the combobox role. Neither case changed timeouts or the scientific equations.
