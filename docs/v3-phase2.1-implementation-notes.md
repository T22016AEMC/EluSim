# Phase 2.1 implementation notes

Changes:
- Fit only preregistered C1/C2/C3/C4 from the existing 273 repository curves.
- Reuse the seed-42 outer Murcko partition: 189 training rows, 84 test rows.
- C4 selects alpha from 0.1, 1, 10 on a separate inner scaffold holdout
  (162 fit rows and 27 tuning rows), then refits outer training rows.
- Standardization is fitted only on the rows used for each fit.
- S = a*logKw+b uses observed outer-training logKw and S. For C2-C4,
  logKw=(logk35+0.35*b)/(1-0.35*a). The script records standardized coefficients,
  means and scales. Serving inference uses the algebraically equivalent logKw
  coefficients and the existing NumPy/RDKit runtime.
- C2 and C4 clear all 19 specified software gates. C2 is selected by the requested
  outer-test logk35 MAE comparison. Those test numbers have participated in
  selection; they are not untouched external experimental evidence.
- Keep version 1 at backend/models/generic-lss-v1.json; version 2.0.0 remains a
  screening estimate under the existing non-commercial data license.
- A/B data and models, method differences, ionization warnings, clipping,
  manual/calibration protection and the LSS solver remain unchanged.
- Add min_segment_min (default 0.5, bounds 0.1-10). Raise total gradient lower
  bounds to segments*minimum; reject an upper bound below that total.
- Allocate each ramp as minimum + normalized_weight*remaining_duration.
  Expose the setting in the existing workspace; preserve the optimizer framework.
- No Render settings, render.yaml or .gitignore changes.

Reproduction commands (PowerShell, repository root):
- .venv/Scripts/python.exe scripts/fit_tier_c_candidates.py
  Records C1-C4 and existing A/B/C outputs without writing serving coefficients.
- .venv/Scripts/python.exe scripts/fit_tier_c_candidates.py --write-model
  Writes the selected equation only if every specified gate clears; keeps v1.
  Use this phase-2.1 command for v2 fitting. fit_generic_lss.py is the historical
  phase-1 fitter and is not the reproduction command for the selected v2 model.
- .venv/Scripts/python.exe scripts/export_phase21.py
- .venv/Scripts/python.exe -m pytest -q
- In frontend: pnpm build; playwright test --reporter=list with ELUSIM_BASE_URL
  pointing to the locally running existing FastAPI app.

Software checks:
- Final complete runs: pytest 108 passed, 0 failed; Playwright 28 passed,
  0 failed (14 desktop and 14 Pixel 7 viewport); frontend build completed.
- test_sanity_ordering.py: 19 forced-C gates, conversion identity and sign/split
  checks. No A/B lookup can satisfy a forced-C gate.
- test_optimize_multisegment.py: 200 seeded decoded vectors for each of 2/3
  segments, minimum duration and monotonic composition, bounds and existing
  seed reproducibility tests.
- optimizer.spec.ts: actual API payload with 0.75 min, returned durations,
  existing map/apply/Pareto/export/cancellation flows on desktop and Pixel 7.
- One initial browser run hit a map API 504 while local tasks overlapped and was
  interrupted. The 30-second production limit was retained. Final complete
  outputs are saved separately in this folder's corresponding review directory.
- One full browser run recorded 27 passes and a debounce timing assertion
  failure: two separate fill operations exceeded 600 ms on the mobile viewport.
  p0-estimation.spec.ts now controls browser time for those two edits and
  checks no request at 599 ms, then advances the final millisecond. The
  product debounce and real API response assertions remain unchanged.
- Existing backend and UV/DAD/legacy-project browser cases are retained.

Pending user checks:
- Compare caffeine/phenol/benzene, benzene/toluene/ethylbenzene/propylbenzene,
  benzyl alcohol/toluene, aniline/benzene, benzene/naphthalene and
  PGMEA/benzyl acetate against user experiments under specified method conditions.
- Inspect all candidate coefficients and numbers:
  review/phase2.1/tier-c-candidate-details.json and tier-c-candidates.csv.
- Inspect each molecule under forced C, old C and current A/B/C:
  review/phase2.1/tier-c-sanity-molecules.csv.
- Inspect fitted residuals: artifacts/generic-lss-fit.csv and its summary;
  version-controlled copies also exist under review/phase2.1.
- Assess whether the chosen minimum segment time is executable on the actual
  instrument. It is a program constraint, not a pump/mixer dynamics calculation.
- Review review/phase2.1/multisegment-demo.json against the user's requirements.
- Scientific scope, retention ordering in actual experiments, ionization,
  extrapolation and suitability remain pending user review.

Limits:
- Training conditions remain ACN/Eclipse Plus C18/35 C/0.1% formic acid/phi 0.2-0.5.
  Generic C18/25 C/5-95% and MeOH are extrapolation, retaining explicit warnings.
- No pKa/logD correction, added transport physics, pressure model or uncertainty
  model. Minimum ramp duration alone does not establish instrument suitability.
- Search time budgets and finite method windows remain as before; ODE comparison
  and process startup are additional to the stochastic-search time budget.
- No physical-phone or empirical-data assessment is performed by the agent.
