# EluSim_V1 science and verification

The production engine is `elusim-lss-migration/1.0.0`, independently implemented with SciPy. PyLSS `d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f` is an unmodified, AGPL reference subset used in an asymptotic linear-gradient comparison, not the general production solver. Reasons: the investigated PyLSS zero-gradient sentinel, missing segmented boundary handling and ambiguous width conversion. NLSS is not shipped. CADET and OpenIEX are not runtime dependencies.

Let normalized column position be x, mobile hold-up volume Vm in mL and cumulative pump volume Q(t)=∫F(t)dt. The pump time at a solute location is τ=Q⁻¹(max(0,Q(t)−Vd−xVm)). The initial composition fills the column before injection. Under plug-flow solvent transport and dilute local equilibrium:

`φ(x,t)=φprogram(τ)`

`k(x,t)=10^(logKw−Sφ(x,t))`

`dx/dt = F(t) / [Vm(1+k(x,t))]`.

The solver stops at x=1, or reports non-elution at the programmed end. Flow varies linearly between nodes and Q is integrated analytically; composition supports linear ramps, holds and steps. Geometric Vm=π d² L ε / 4000 with d and L in mm. All times are minutes, all flow rates mL/min. Dwell is a solvent-front delay, not a blanket additive delay to every compound. Temperature-dependent selectivity is not validated; temperature gradients are rejected. Parameters bound to a scope are rejected outside stationary phase, solvent A/B, buffer, pH or temperature.

Migration/retention principles: [migration and elution equations](https://www.sciencedirect.com/science/article/pii/S0021967319303255), [open-access solvent-front treatment](https://pmc.ncbi.nlm.nih.gov/articles/PMC6480021/), and the original LSS/PyLSS references recorded in the retained research. No source code from these papers was copied. This mathematical derivation is a model assumption, not a claim that HILIC obeys this RP implementation.

## Width and resolution

When a plate count N is supplied, screening sigma is `sqrt(Rt²/N + (Vinjection/Finitial)²/12 + sigmaextra²)`. Base width=4 sigma, FWHM=2 sqrt(2 ln2) sigma. Gaussian peak height is relative response, not injected mass. Adjacent-pair `Rs=2 ΔRt/(Wbase1+Wbase2)`. No peak or Rs is created without sufficient efficiency data. No gradient-compression, overload, asymmetry or pressure accuracy is claimed. Synthetic profiles must remain labelled Screening only; calibration residuals are not external prediction error.

## Actual tests

`pytest -q --junitxml=artifacts/backend-tests.xml`: **20 passed** on Python 3.12, with a Starlette/httpx deprecation warning. Covered:

- Isocratic analytic Rt=Vm/F(1+k), including zero slope.
- Split-linear-segment invariance; DOP853 step/tolerance convergence.
- Column length, flow, gradient duration and dwell-front sensitivity.
- Variable-flow cumulative-volume inverse and step/hold program.
- Non-eluted, insufficient structure model, unsupported mode and temperature boundaries.
- Gaussian FWHM/base-width/Rs identities; no-efficiency behaviour.
- Scope checks, bounded optimization and two-method synthetic parameter recovery / identifiability.
- High-retention linear-gradient PyLSS reference comparison (limited asymptotic domain, not universal equality).
- Actual child-process timeout termination / capacity release; RDKit, import, payload and rate limits.

These are numerical / software tests. **No external experimental LC dataset was used to validate V1 accuracy.** NP, HILIC, IEX, SEC and non-small-molecule quantitative predictions remain unsupported. The API has separate parameter names / capability entries for these modes and never substitutes the RP equation.

Local browser suite: **4 passed** across desktop and Pixel 7 emulation, using built React + FastAPI. Tested RDKit descriptors, node edits, real simulations, ECharts, optimization/application, refresh, unsupported modes, JS errors and horizontal overflow. Public HTTPS results are recorded separately; local tests are not public acceptance. No physical phone / cellular-network result is implied.
