# Scientific model artifacts

Application inference code is AGPL-3.0-or-later. Each independent JSON artifact has its own license and scope in metadata:

- report0259-rt 2.0.0: CC BY-SA 4.0; exact RepoRT0259 method-specific Rt only.
- pnnl-uv-shape 2.0.1: CC BY 4.0; 220–400 nm normalized experimental spectrum shape.
- lss-parameters 2.1.0: CC BY-NC-SA 3.0 US; experimental QSRR from Boswell isocratic data via Wiczling curation. Non-commercial only. See ../../data/retention/LICENSE.md.

LSS weights and experimental curve data are separate licensed data artifacts, not relicensed AGPL code. Preserve attribution, modifications and share-alike terms when distributing them. Safe JSON inference uses no pickle execution, Torch or server-side sklearn. Heldout errors are in docs/v2-evidence; no confidence percentages or external gradient Rt validation are claimed.
