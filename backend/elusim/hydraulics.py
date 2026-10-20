"""Inlet-composition pressure estimate with user-specified flow resistance."""

import math
import numpy as np
from scipy.interpolate import interp1d

# Guillarme, Heinisch & Rocca, J. Chromatogr. A 1052 (2004), 39-51,
# Table 2, doi:10.1016/j.chroma.2004.08.052.
# Source table in cP; subset 25, 60, 90 C and volume fractions 0:0.2:1.
# Only published physical values, not source program code.
TEMPERATURES = np.array([25.0, 60.0, 90.0])
FRACTIONS = np.linspace(0, 1, 6)
TABLES = {
    "ACN": np.array([
        [0.89, 0.98, 0.89, 0.72, 0.52, 0.35],
        [0.53, 0.59, 0.55, 0.52, 0.43, 0.31],
        [0.39, 0.40, 0.39, 0.38, 0.34, 0.24],
    ]),
    "MeOH": np.array([
        [0.89, 1.40, 1.62, 1.54, 1.12, 0.56],
        [0.53, 0.68, 0.74, 0.72, 0.60, 0.35],
        [0.38, 0.44, 0.45, 0.47, 0.42, 0.26],
    ]),
}


def water_viscosity(temperature_c):
    """Vogel water equation: 2.414e-5*10**(247.8/(TK-140)) Pa s.

    Reid, Prausnitz & Poling, The Properties of Gases and Liquids,
    4th ed. (1987); engineering correlation, liquid water, 0-100 C here.
    """
    return 2.414e-5 * 10 ** (247.8 / (temperature_c + 273.15 - 140))


def table_at_temperature(solvent, temperature_c):
    """Log-linear interpolation/extrapolation of the cited 25-90 C table."""
    interpolator = interp1d(
        TEMPERATURES, np.log(TABLES[solvent]), axis=0,
        bounds_error=False, fill_value="extrapolate",
    )
    return np.exp(interpolator(temperature_c)) * 1e-3


def organic_viscosity(solvent, temperature_c):
    """Return pure organic endpoint from the cited temperature table, Pa s."""
    return float(table_at_temperature(solvent, temperature_c)[-1])


def correlation_log10_cp(phi, solvent, temperature_c):
    """Guillarme et al. (2004), equations 26/27, log10(eta in cP).

    Coefficients of 1/T are expressed here with T in kelvin (the displayed
    paper coefficients use 10^-3 K temperature). phi is organic volume fraction.
    Published application covers 25-180 C; this implementation restricts its
    shared organic-endpoint table scope to 25-90 C.
    """
    fraction = np.asarray(phi, dtype=float)
    inverse_temperature = 1000 / (temperature_c + 273.15)
    if solvent == "MeOH":
        return (
            -2.429 + .714*inverse_temperature - 1.859*fraction
            + .9117*fraction*inverse_temperature + 1.8586*fraction**2
            - .9681*fraction**2*inverse_temperature
        )
    return (
        -2.063 + .6019*inverse_temperature + .0709*fraction
        + .062*fraction*inverse_temperature + .5043*fraction**2
        - .3458*fraction**2*inverse_temperature
    )


def viscosity(phi, solvent, temperature_c):
    """Use the cited empirical curvature with explicit endpoint normalization.

    log10(eta)=log10(eta_G(phi))-(1-phi)*log10(eta_G(0))
      -phi*log10(eta_G(1))+(1-phi)*log10(eta_water)+phi*log10(eta_organic).
    Guillarme et al. equations 26/27 supply the nonideal composition curvature;
    normalization enforces the requested Vogel water and tabulated organic
    endpoints. This adaptation is explicit, not the unmodified published fit.
    Effective scope: 25-90 C, phi 0-1, ambient-pressure aqueous ACN/MeOH.
    No pressure dependence, buffer/salt correction or axial integration.
    """
    fraction = np.asarray(phi, dtype=float)
    water = water_viscosity(temperature_c)
    organic = organic_viscosity(solvent, temperature_c)
    excess = (
        correlation_log10_cp(fraction, solvent, temperature_c)
        - (1-fraction)*correlation_log10_cp(0, solvent, temperature_c)
        - fraction*correlation_log10_cp(1, solvent, temperature_c)
    )
    return 10 ** ((1-fraction)*np.log10(water)+fraction*np.log10(organic)+excess)


def column_pressure_bar(column, flow_ml_min, viscosity_pa_s):
    """Darcy packed-bed form: DP=Phi*eta*L*us/dp**2; Pa -> bar.

    Snyder, Kirkland & Dolan, Introduction to Modern Liquid Chromatography,
    3rd ed. (2010), packed-column pressure/permeability relation.
    Phi is a user-provided dimensionless resistance; no porosity factor is
    applied again. Superficial us=F/area, with SI unit conversion.
    """
    area = math.pi * (column.diameter_mm * 1e-3 / 2)**2
    velocity = np.asarray(flow_ml_min) * 1e-6 / 60 / area
    return (
        column.flow_resistance * viscosity_pa_s * column.length_mm * 1e-3
        * velocity / (column.particle_um * 1e-6)**2 / 1e5
    )


def pressure_warnings(method):
    """Expose range and composition limitations as Chinese notices."""
    notices = ["壓力以管柱入口組成估算，未積分管柱內軸向黏度差；未含壓力對黏度的影響。"]
    if not 25 <= method.column.temperature_c <= 90:
        notices.append("黏度表適用 25–90 °C；目前溫度為外推。")
    if method.mobile.a != "Water" or method.mobile.buffer not in ("None", ""):
        notices.append("黏度關係只含水／ACN 或水／MeOH，未計入緩衝液及添加物。")
    return notices


def pressure_profile(method, program):
    """Sample >=201 times plus knots, using the actual transported inlet."""
    grid = np.unique(np.r_[np.linspace(0, program.t[-1], 201), program.t])
    fraction = np.array([
        program.local_phi(t, 0, 0, method.mobile.dwell_ml) for t in grid
    ])
    eta = viscosity(fraction, method.mobile.b, method.column.temperature_c)
    column_bar = column_pressure_bar(method.column, np.interp(grid, program.t, program.f), eta)
    total = column_bar + method.mobile.system_pressure_bar
    index = int(np.argmax(total))
    return {
        "available": True,
        "max_pressure_bar": float(total[index]),
        "time_at_max_min": float(grid[index]),
        "column_pressure_at_max_bar": float(column_bar[index]),
        "system_pressure_bar": method.mobile.system_pressure_bar,
        "warnings": pressure_warnings(method),
        "reason": "入口組成取樣壓力估算；流阻因子為使用者輸入。",
    }


def batch_max_pressure(method, node_sets):
    """Vectorize >=201 samples across constant-flow, mixer-free candidates."""
    times = np.array([[node.time_min for node in nodes] for nodes in node_sets])
    fractions = np.array([[node.b_percent / 100 for node in nodes] for nodes in node_sets])
    steps = np.array([[node.interpolation == "step" for node in nodes] for nodes in node_sets])
    flow = method.gradient[0].flow_ml_min
    grid = np.sort(np.c_[times[:, -1, None] * np.linspace(0, 1, 201), times], axis=1)
    transported = np.maximum(0, grid - method.mobile.dwell_ml / flow)
    phi = np.broadcast_to(fractions[:, :1], grid.shape).copy()
    for index in range(times.shape[1]-1):
        ratio = np.clip(
            (transported-times[:, index, None]) /
            (times[:, index+1]-times[:, index])[:, None], 0, 1,
        )
        local = fractions[:, index, None] + ratio * (fractions[:, index+1]-fractions[:, index])[:, None]
        local = np.where(steps[:, index, None], fractions[:, index, None], local)
        phi = np.where(transported >= times[:, index, None], local, phi)
    phi = np.where(transported >= times[:, -1, None], fractions[:, -1, None], phi)
    eta = viscosity(phi, method.mobile.b, method.column.temperature_c)
    total = column_pressure_bar(method.column, flow, eta) + method.mobile.system_pressure_bar
    return total.max(axis=1)
