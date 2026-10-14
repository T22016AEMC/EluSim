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

- Dilute equilibrium `log10 k = logKw − Sφ`, position-dependent delayed solvent front, numerical migration until column exit.
- Constant temperature with supplied selectivity parameters. pH / solvent / stationary-phase transfers require matching parameter scope.
- Gaussian screening widths from explicit plate count, injection variance and extra-column sigma. No validated gradient compression, tailing or overload model.
- Optimization enumerates bounded gradients, evaluates actual simulations and marks unfeasible candidates. Pressure is not calculated without a validated viscosity/permeability model.
- Two or more independent methods may fit logKw/S; rank/condition checks reject unidentifiable fits. Fit residual is not external prediction error.
- RDKit structure descriptors do not generate arbitrary retention parameters; the structure-prediction interface reports missing validated models.
- Projects remain in the visitor's browser; no anonymous shared project database.

## License

AGPL-3.0-or-later, full text in LICENSE. Pinning, upstream notices, provenance and modifications are in [NOTICE](NOTICE.md). Deployed corresponding-source download is available in Model & Column Library and `/api/source`.
