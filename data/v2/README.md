# Versioned scientific data
Raw files remain unchanged; manifest.json pins URLs, commits and SHA256.

RepoRT0259: CC-BY-SA-4.0; attribution to F. Kretschmer, E.-M. Harrieder, M. A. Hoffmann, S. Böcker, M. Witting, RepoRT (Nat Methods 2024), https://doi.org/10.1038/s41592-023-02143-z . See LC-LICENSE. Derived LC model, cleaned labels and split metadata use CC-BY-SA-4.0. No endorsement.

UV_w_SMILES: PNNL-CompBio/ML_UVvisModels, Copyright Battelle Memorial Institute, BSD-2-Clause, see UV-LICENSE. McNaughton et al., JCIM 2023, https://doi.org/10.1021/acs.jcim.2c01662 . Repository-provided experimental relative spectra: 220–400nm at 1nm, as confirmed by upstream plot.py. Original data are not molar absorptivity and CSV contains no solvent/pH labels. Derived UV model uses BSD-2-Clause.

Models are trained locally with scikit-learn 1.7.2, not copied pretrained weights. The server requires only existing NumPy/SciPy/RDKit. Scaffold grouped heldout records are not independent lab validation. Full source and data for reproducing training are included in the deployment source archive. No private user data are included.
