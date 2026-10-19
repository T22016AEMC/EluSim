# EluSim_V2

Incremental scientific prediction upgrade of EluSim_V1. Public entry remains https://elusim-v1.onrender.com/ .

Two CPU models trained from real licensed public data: exact-method RepoRT0259 Rt (not logKw/S) and PNNL experimental relative UV shape 220–400nm. Both are **experimental**, scaffold-heldout tested, with descriptor/fingerprint applicability abstention. No universal C18 transfer, pKa, solvent UV correction or extinction coefficient claim. Known/calibrated V1 LSS, peaks, Rs and optimizer remain available.

Model cards, licenses, validation and incomplete LSS structure-parameter path: [V2 scientific review](docs/elusim-v2-model-review.md). Raw data/source hashes: data/v2/manifest.json. Safe compressed JSON weights: backend/models. AGPL source archive includes data and training scripts.

Train offline with backend requirements plus scripts/training-requirements.txt; run scripts/fetch_v2_data.py then scripts/train_v2_models.py. Serving requires only original backend lockfile. To train future LSS parameters from identifiable experimental curves, use scripts/train_lss_model.py; no synthetic production model is supplied.

---

# EluSim_V1

**EluSim_V1 — LC Separation Simulation & Gradient Optimization**

Server-side FastAPI / RDKit / SciPy and a responsive React / ECharts workbench. RP local-equilibrium LSS uses supplied or calibrated parameters; NP/HILIC/IEX/SEC have explicit, separate capability boundaries and do not run the RP equation. Original research is preserved in `docs/`.

## Run

```sh
python -m venv .venv
# Activate .venv using your operating system's normal activation command.
pip install -r backend/requirements.lock
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm build
cd ..
python scripts/package_source.py
python -m pytest
PYTHONPATH=backend uvicorn elusim.main:app --host 127.0.0.1 --port 8000
```

Windows: `$env:PYTHONPATH='backend'; .venv/Scripts/python.exe -m uvicorn elusim.main:app --host 127.0.0.1 --port 8000`.

Production: `docker compose up --build`. Same container serves `/` and `/api`; see [deployment](docs/elusim-v1-deployment.md). A local URL is not public deployment acceptance.

## Scientific boundaries

- Dilute equilibrium `log10 k = logKw − Sφ`, delayed plug-flow solvent transport, and numerical migration to the column outlet.
- Column width uses `G·t0_e·(1+k_e)/√N`, with the requested Poppe factor or `band_compression=none` (G=1). Injection and extra-column variances remain additive. Multiple gradient segments use a local outlet approximation; steps use the post-event slope. Formula reference: [Poppe et al., J. Chromatogr. 204 (1981), 77–84](https://doi.org/10.1016/S0021-9673(00)81641-6).
- Parameter tiers are A stored measured-curve LSS fit, B existing scoped QSRR, C generic C18 regression, D user experimental calibration, and M manual. Coefficients and results carry `validation_status: "unvalidated — pending user validation"`.
- The C regression uses only repository ACN / Eclipse Plus C18 / 35°C / 0.1% formic-acid curves over φ 0.2–0.5. Other conditions, including MeOH, are extrapolation. No pKa, microstate, logD or ionization correction is calculated.
- Changes in stationary phase, solvent, pH, temperature, particles, structure or gradient range produce warnings and retain numerical LSS parameters. Numerical availability does not establish suitability for an experiment. Other LC modes and unsupported entity types remain outside this workflow.
- M/D parameters are protected from background estimates. A/B/C are refreshed after structure/method edits; explicit re-estimation can replace M. Calibration takes priority.
- Optimization keeps the existing bounded candidate grid and uses the same migration/width calculations. Pressure, tailing and overload are not modeled in this phase.
- Two or more independent methods are required for logKw/S calibration, with rank and condition checks. All scientific/data checks remain for the user; software tests cover equations, API behavior and UI flows only.
- Projects remain in the visitor's browser; no anonymous shared project database. This branch does not change the deployed website.

## License

AGPL-3.0-or-later, full text in LICENSE. Pinning, upstream notices, provenance and modifications are in [NOTICE](NOTICE.md). Deployed corresponding-source download is available in Model & Column Library and `/api/source`.
