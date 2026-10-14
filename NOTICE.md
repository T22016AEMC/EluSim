# EluSim_V1 notices

EluSim_V1 is provided under AGPL-3.0-or-later. The independent LSS migration ODE, API, interface and deployment configuration were developed for this project. All source and build instructions are included in `/api/source` on a deployed build. The UI links to the corresponding source and full license.

PyLSS © Giuseppe Marco Randazzo, AGPL-3.0-or-later, https://github.com/gmrandazzo/PyLSS at d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f. `third_party/pylss/{ssengine,optimizer,miscalgoritms}.py` is an unmodified reference subset; provenance and SHA256 are recorded. Only `__init__.py` packaging was added. The upstream NLSS path and zero-gradient sentinel are not used by the production model. This is not an upstream PyLSS release or endorsement.

NumPy, SciPy, RDKit, FastAPI/Pydantic, React, Vite, TypeScript and ECharts retain their respective licenses. Exact installed versions are in `backend/requirements.lock` and `frontend/pnpm-lock.yaml`; distribution license evidence is recorded separately before release. Full installed Python and bundled JavaScript runtime notices are in `third_party/RUNTIME_LICENSES.txt`; binary wheel vendor licenses still apply, including platform-specific notices on Linux. No GRIP, CADET, OpenIEX, unlicensed training code or external pretrained weights are deployed.

Synthetic parameters and curves in the default project are demonstration/screening data, not measured experimental chromatography. LSS parameters cannot be inferred from RDKit descriptors without a separately validated model.

V2 scientific data and derived model weights have independent licenses: see data/v2/README.md and backend/models/README.md. RepoRT-derived artifacts: CC-BY-SA-4.0; PNNL software: BSD-2-Clause; original UV data and derived UV weights: CC-BY-4.0. Training uses scikit-learn 1.7.2 (BSD-3-Clause); serving retains existing dependencies only.

Correction: Original UV data and our derived UV model2.0.1 are CC-BY-4.0, attributed to Urbina et al. (Figshare15217512.v3), with PNNL preprocessing credited. PNNL BSD-2-Clause notice applies separately to software; it is not used to infer upstream data rights. Two untraceable records were excluded. See data/v2/README.md, UV-DATA-LICENSE and docs/v2-evidence/uv-data-provenance.json.


Scoped retention data / lss-parameters 2.1.0: CC BY-NC-SA 3.0 US, separately licensed from application code. Credit: Paul Boswell and retentionprediction.org contributors, and Paweł Wiczling / Agnieszka Kamedulska / Łukasz Kubik for curated data/structure mapping. Source: https://www.retentionprediction.org/hplc/database/ and https://github.com/wiczling/isocratic-qsrr/tree/2951822d97bd76eeeb244989c9e1691ca4a1ff88 . Non-commercial service authorized by the owner on 2026-10-14. Derivatives (curated curves and weights) retain CC BY-NC-SA 3.0 US. See data/retention/LICENSE.md. This notice does not impose NC restrictions on independently licensed AGPL application code. No endorsement or scientific warranty is implied.
