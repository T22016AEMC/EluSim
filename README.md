# EluSim_V2

Incremental scientific prediction upgrade of EluSim_V1. Public entry remains https://elusim-v1.onrender.com/ .

Two CPU models trained from real licensed public data: exact-method RepoRT0259 Rt (not logKw/S) and PNNL experimental relative UV shape 220–400nm. Both are **experimental**, scaffold-heldout tested, with descriptor/fingerprint applicability abstention. No universal C18 transfer, pKa, solvent UV correction or extinction coefficient claim. Known/calibrated V1 LSS, peaks, Rs and optimizer remain available.

Model cards, licenses, validation and incomplete LSS structure-parameter path: [V2 scientific review](docs/elusim-v2-model-review.md). Raw data/source hashes: data/v2/manifest.json. Safe compressed JSON weights: backend/models. AGPL source archive includes data and training scripts.

Train offline with backend requirements plus scripts/training-requirements.txt; run scripts/fetch_v2_data.py then scripts/train_v2_models.py. Serving requires only original backend lockfile. To train future LSS parameters from identifiable experimental curves, use scripts/train_lss_model.py; no synthetic production model is supplied.

---

# EluSim_V1

**EluSim_V1 — LC Separation Simulation & Gradient Optimization**

Server-side FastAPI / RDKit / SciPy and a React / ECharts workbench focused on desktop browsers. RP local-equilibrium LSS uses supplied or calibrated parameters; NP/HILIC/IEX/SEC have explicit, separate capability boundaries and do not run the RP equation. Original research is preserved in `docs/`.

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

- Dilute equilibrium LSS with delayed plug-flow solvent transport. At constant flow, migration uses an exact piecewise closed-form integral for linear, hold and step programs; variable flow uses the existing ODE. Both apply the finite programmed run window.
- Column width uses `G·t0_e·(1+k_e)/√N`, with the requested Poppe factor or `band_compression=none` (G=1). Injection and extra-column variances remain additive. Multiple gradient segments use a local outlet approximation; steps use the post-event slope. Formula reference: [Poppe et al., J. Chromatogr. 204 (1981), 77–84](https://doi.org/10.1016/S0021-9673(00)81641-6).
- Parameter tiers are A stored measured-curve LSS fit, B existing scoped QSRR, C generic C18 regression, D user experimental calibration, and M manual. Coefficients and results carry `validation_status: "unvalidated — pending user validation"`.
- The C regression uses only repository ACN / Eclipse Plus C18 / 35°C / 0.1% formic-acid curves over φ 0.2–0.5. Other conditions, including MeOH, are extrapolation. No pKa, microstate, logD or ionization correction is calculated. Version 2 fits constrained logk at φ=0.35 and algebraically converts through the train-group S/logKw relation; version 1 is retained as generic-lss-v1.json. Candidate gates are software checks for the requested examples, not experimental evidence.
- Changes in stationary phase, solvent, pH, temperature, particles, structure or gradient range produce warnings and retain numerical LSS parameters. Numerical availability does not establish suitability for an experiment. Other LC modes and unsupported entity types remain outside this workflow.
- M/D parameters are protected from background estimates. A/B/C are refreshed after structure/method edits; explicit re-estimation can replace M. Calibration takes priority.
- Resolution maps enumerate a bounded constant-flow grid using the piecewise integral. Multi-segment optimization is stochastic search within a time budget; no global optimality claim. Leading map rows and the multi-segment result include ODE numerical differences. The legacy optimization API remains available. Pressure, tailing and overload are not modeled in this phase. Each ramp has a configurable minimum duration (default 0.5 min, bounds 0.1–10 min); total gradient lower bounds rise to the sum of these minima. This does not model pump or mixer dynamics.
- Two or more independent methods are required for logKw/S calibration, with rank and condition checks. All scientific/data checks remain for the user; software tests cover equations, API behavior and UI flows only.
- Projects remain in the visitor's browser; no anonymous shared project database. Publication follows the separate Git/CI/health procedure; local checks do not establish deployment.

## License

AGPL-3.0-or-later, full text in LICENSE. Pinning, upstream notices, provenance and modifications are in [NOTICE](NOTICE.md). Deployed corresponding-source download is available in Model & Column Library and `/api/source`.

### 瀏覽器支援範圍

自階段 2.2 起，以桌面瀏覽器為主，程式流程測試僅執行桌面 Chromium。既有響應式樣式保留，但不再維護手機排版、觸控或窄螢幕操作。

### 階段 2.2 桌面工作區

介面使用台灣繁體中文；參數來源自動判定，手動值與實驗校正受到保護。
首次開啟及重設使用空白清單，可主動按「載入示範混合物」。
梯度欄位依目前溶劑顯示 ACN／MeOH；來源徽章使用文字，CSV 保留來源代碼並另附中文標籤。
舊專案內容保留，參數來源頁改為唯讀資訊。
本機與 CI 的程式回歸略過使用者保留自行檢查的合理性門檻檔案。
詳見 [階段 2.2 實作紀錄](docs/v3-phase2.2-implementation-notes.md)。


### 階段 3A 選用物理設定
混合器體積預設 0，柱效預設固定理論板數，壓力上限預設不限。
混合槽會抹平梯度，並在既有延遲體積外額外增加平均延遲；啟用時改用 ODE。
Knox 柱效的 A/B/C、Dm 與流阻因子是典型參考值，未經驗證。
壓力以入口組成及文獻黏度表取樣估算；未積分管柱內黏度分布。
公式、範圍與待使用者確認事項見 docs/v3-phase3a-implementation-notes.md。
