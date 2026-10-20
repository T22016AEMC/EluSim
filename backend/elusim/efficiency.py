"""Reduced Knox plate-height equation with explicit SI conversions."""

import math


def reduced_height(nu, a, b, c):
    """Return h=A*nu**(1/3)+B/nu+C*nu for positive reduced velocity.

    Knox, J. Chromatogr. Sci. 15 (1977), 352-364,
    doi:10.1093/chromsci/15.8.352. Coefficients are user inputs.
    """
    return a * nu**(1 / 3) + b / nu + c * nu


def effective_plates(column, flow_ml_min):
    """Return fixed N unchanged, or L/(h*dp) at the supplied elution flow.

    Interstitial u=F/(area*total porosity); all lengths and flow use SI here.
    Dm and A/B/C are reference inputs awaiting user experimental review.
    """
    if column.efficiency_model == "fixed":
        return column.plates
    area_m2 = math.pi * (column.diameter_mm * 1e-3 / 2)**2
    velocity = flow_ml_min * 1e-6 / 60 / (area_m2 * column.porosity)
    particle_m = column.particle_um * 1e-6
    nu = velocity * particle_m / column.diffusion_m2_s
    height = reduced_height(nu, column.vd_a, column.vd_b, column.vd_c)
    return column.length_mm * 1e-3 / (height * particle_m)
