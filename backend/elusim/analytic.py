"""Piecewise LSS migration for constant-flow plug transport.

References: Snyder & Dolan, High-Performance Gradient Elution (Wiley, 2007);
Poppe et al., J. Chromatogr. 204 (1981) 77–84; Schoenmakers et al.,
J. Chromatogr. 205 (1981) 13–30. Equations implemented independently.
With u=t-x*t0, dx=du/(t0*k(phi(u-tD))). Elution therefore requires
integral(du/k)=t0 and tR=u_e+t0. On a ramp k=k_a*exp(-beta*du),
the integral is expm1(beta*du)/(beta*k_a), inverted with log1p.
Steps hold the left composition until the following node; the final hold
extends indefinitely. The caller applies its finite run-time window.
"""

import math

import numpy as np

from .engine import RetentionState


def analytic_state(
    program_times, program_phis, steps, logkw, s, flow, void_ml, dwell_ml
):
    """Return a scalar outlet event, or None when flow is not constant."""
    flows = np.asarray(flow, dtype=float)
    if not np.all(flows == flows.flat[0]):
        return None
    flow_value = float(flows.flat[0])
    t0 = void_ml / flow_value
    delay = dwell_ml / flow_value
    times = np.asarray(program_times, dtype=float)
    phis = np.asarray(program_phis, dtype=float)
    remaining = t0
    intervals = [(0.0, delay, phis[0], 0.0)]
    for index in range(len(times) - 1):
        slope = (
            0.0
            if steps[index]
            else (phis[index + 1] - phis[index]) / (times[index + 1] - times[index])
        )
        intervals.append(
            (delay + times[index], delay + times[index + 1], phis[index], slope)
        )
    intervals.append((delay + times[-1], math.inf, phis[-1], 0.0))
    for start, end, phi, slope in intervals:
        if end <= start:
            continue
        k_start = 10.0 ** (logkw - s * phi)
        beta = s * math.log(10.0) * slope
        capacity = (end - start) / k_start
        if beta != 0:
            exponent = beta * (end - start)
            capacity = math.expm1(min(exponent, 700.0)) / (beta * k_start)
        if remaining < capacity or math.isinf(end):
            duration = (
                remaining * k_start
                if beta == 0
                else math.log1p(beta * k_start * remaining) / beta
            )
            phi_end = phi + slope * duration
            return RetentionState(
                rt_min=float(start + duration + t0),
                phi_outlet=float(phi_end),
                k_e=float(10.0 ** (logkw - s * phi_end)),
                flow_at_elution=flow_value,
                dphi_dt_outlet=float(slope),
            )
        remaining = max(0.0, remaining - capacity)
    return None


def analytic_batch(
    program_times, program_phis, steps, logkw, s, flow, void_ml, dwell_ml
):
    """Compute candidate-by-compound outlet arrays using NumPy segment masks.

    Times/phis/steps have shape (candidates, nodes), or a single node vector.
    Parameters have shape (compounds,). Constant scalar flow is required.
    Widths remain the caller responsibility so the existing convention is shared.
    """
    times = np.atleast_2d(np.asarray(program_times, dtype=float))
    phis = np.atleast_2d(np.asarray(program_phis, dtype=float))
    steps = np.broadcast_to(np.asarray(steps, dtype=bool), times.shape)
    if np.ndim(flow) and not np.all(np.asarray(flow) == np.asarray(flow).flat[0]):
        return None
    flow = float(np.asarray(flow).flat[0])
    t0 = void_ml / flow
    delay = dwell_ml / flow
    logkw = np.asarray(logkw, dtype=float)[None, :]
    strength = np.asarray(s, dtype=float)[None, :]
    shape = (len(times), logkw.size)
    remaining = np.full(shape, t0)
    result = {
        key: np.full(shape, np.nan)
        for key in ("rt_min", "phi_outlet", "k_e", "dphi_dt_outlet")
    }
    active = np.ones(shape, dtype=bool)
    starts = np.column_stack((np.zeros(len(times)), times + delay))
    ends = np.column_stack(
        (np.full(len(times), delay), times[:, 1:] + delay, np.full(len(times), np.inf))
    )
    initial_phis = np.column_stack((phis[:, 0], phis))
    ramp_slopes = np.where(steps[:, :-1], 0.0, np.diff(phis) / np.diff(times))
    slopes = np.column_stack((np.zeros(len(times)), ramp_slopes, np.zeros(len(times))))
    for segment in range(starts.shape[1]):
        start = starts[:, segment, None]
        duration = ends[:, segment, None] - start
        phi = initial_phis[:, segment, None]
        slope = slopes[:, segment, None]
        k_start = 10.0 ** (logkw - strength * phi)
        beta = strength * math.log(10.0) * slope
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            capacity = np.where(
                beta == 0,
                duration / k_start,
                np.expm1(np.minimum(beta * duration, 700.0)) / (beta * k_start),
            )
            hit = (
                active & (duration > 0) & ((remaining < capacity) | np.isinf(duration))
            )
            argument = np.where(hit, beta * k_start * remaining, 0.0)
            delta = np.where(beta == 0, remaining * k_start, np.log1p(argument) / beta)
        phi_end = phi + slope * delta
        result["rt_min"][hit] = np.broadcast_to(start + delta + t0, shape)[hit]
        result["phi_outlet"][hit] = np.broadcast_to(phi_end, shape)[hit]
        result["k_e"][hit] = (10.0 ** (logkw - strength * phi_end))[hit]
        result["dphi_dt_outlet"][hit] = np.broadcast_to(slope, shape)[hit]
        active &= ~hit
        remaining = np.where(active, np.maximum(0.0, remaining - capacity), 0.0)
    result["flow_at_elution"] = np.full(shape, flow)
    return result
