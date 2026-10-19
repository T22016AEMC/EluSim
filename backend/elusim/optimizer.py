"""Bounded grid and differential-evolution search using the common LSS equations."""

import json
import math
import time

import numpy as np
from scipy.optimize import differential_evolution

from .analytic import analytic_batch
from .engine import (
    Program,
    band_width,
    eligibility,
    parameter_warnings,
    retention_state,
    volume,
)
from .schemas import Node
from .estimation import parameter_tier


def prepare(simulation):
    """Resolve structures once, then require every component and efficiency."""
    from .prediction import prepare_structure

    base, _ = prepare_structure(simulation)
    failures = [
        f"{compound.name} ({compound.id}): {eligibility(base, compound)[1]}"
        for compound in base.compounds
        if eligibility(base, compound)[1]
    ]
    if failures:
        raise ValueError("; ".join(failures))
    if len(base.compounds) < 2 or not base.column.plates:
        raise ValueError(
            "Search requires at least two components and column efficiency"
        )
    return base


def nodes_for(base, start, ends, durations, initial_hold, final_hold):
    """Construct strictly timed ramps and optional holds."""
    flow = base.gradient[0].flow_ml_min
    temperature = base.column.temperature_c
    nodes = [
        Node(
            time_min=0,
            b_percent=float(start),
            flow_ml_min=flow,
            temperature_c=temperature,
        )
    ]
    elapsed = initial_hold
    if initial_hold:
        nodes.append(nodes[0].model_copy(update={"time_min": initial_hold}))
    for end, duration in zip(ends, durations):
        elapsed += float(duration)
        nodes.append(
            Node(
                time_min=elapsed,
                b_percent=float(end),
                flow_ml_min=flow,
                temperature_c=temperature,
            )
        )
    if final_hold:
        nodes.append(nodes[-1].model_copy(update={"time_min": elapsed + final_hold}))
    return nodes


def evaluate(base, node_sets):
    """Evaluate candidate arrays and use the phase-one width definition.

    Poppe et al., J. Chromatogr. 204 (1981) 77–84. Local outlet
    approximation for multiple ramps; no empirical conclusion is inferred.
    """
    times = np.array([[node.time_min for node in nodes] for nodes in node_sets])
    phis = np.array([[node.b_percent / 100 for node in nodes] for nodes in node_sets])
    steps = np.array(
        [[node.interpolation == "step" for node in nodes] for nodes in node_sets]
    )
    flow = base.gradient[0].flow_ml_min
    t0 = volume(base.column) / flow
    strength = np.array([compound.s for compound in base.compounds])[None, :]
    logkw = np.array([compound.logkw for compound in base.compounds])[None, :]
    states = analytic_batch(
        times,
        phis,
        steps,
        logkw.ravel(),
        strength.ravel(),
        flow,
        volume(base.column),
        base.mobile.dwell_ml,
    )
    rt = states["rt_min"]
    k0 = 10 ** (logkw - strength * phis[:, :1])
    steepness = t0 * strength * math.log(10) * states["dphi_dt_outlet"]
    poppe_p = k0 * steepness / (1 + k0)
    compression = np.ones_like(rt)
    if base.band_compression == "poppe":
        denominator = np.abs(1 + poppe_p)
        compression = np.divide(
            np.sqrt(1 + poppe_p + poppe_p**2 / 3),
            denominator,
            out=np.ones_like(rt),
            where=denominator > 1e-12,
        )
    sigma_col = compression * t0 * (1 + states["k_e"]) / math.sqrt(base.column.plates)
    sigma = np.sqrt(
        sigma_col**2
        + (base.mobile.injection_ul / 1000 / flow) ** 2 / 12
        + base.mobile.extra_sigma_min**2
    )
    eluted = rt <= times[:, -1, None]
    all_eluted = np.all(eluted, axis=1)
    order = np.argsort(rt, axis=1, kind="stable")
    sorted_rt = np.take_along_axis(rt, order, axis=1)
    sorted_sigma = np.take_along_axis(sigma, order, axis=1)
    resolutions = np.diff(sorted_rt) / (
        2 * (sorted_sigma[:, :-1] + sorted_sigma[:, 1:])
    )
    minimum = np.min(resolutions, axis=1)
    critical = np.argmin(resolutions, axis=1)
    runtime = np.max(rt + 3 * sigma, axis=1)
    return {
        **states,
        "sigma_min": sigma,
        "sigma_col_min": sigma_col,
        "compression_factor": compression,
        "eluted": eluted,
        "all_eluted": all_eluted,
        "min_rs": minimum,
        "run_time_min": runtime,
        "order": order,
        "resolutions": resolutions,
        "critical": critical,
    }


def candidate(base, nodes, values, index, target, maximum):
    """Serialize one candidate without chromatogram grids or model weights."""
    all_eluted = bool(values["all_eluted"][index])
    minimum = float(values["min_rs"][index]) if all_eluted else None
    runtime = float(values["run_time_min"][index]) if all_eluted else None
    order = values["order"][index]
    pair_index = values["critical"][index]
    pair = (
        [base.compounds[int(order[pair_index + offset])].id for offset in (0, 1)]
        if all_eluted
        else None
    )
    peaks = []
    for position, compound_index in enumerate(order):
        compound = base.compounds[int(compound_index)]
        eluted = bool(values["eluted"][index, compound_index])
        peaks.append(
            {
                "id": compound.id,
                "name": compound.name,
                "parameter_tier": parameter_tier(compound),
                "rt_min": (
                    float(values["rt_min"][index, compound_index]) if eluted else None
                ),
                "sigma_min": (
                    float(values["sigma_min"][index, compound_index])
                    if eluted
                    else None
                ),
                "eluted": eluted,
                "rs_to_next": (
                    float(values["resolutions"][index, position])
                    if all_eluted and position < len(order) - 1
                    else None
                ),
            }
        )
    return {
        "gradient": [node.model_dump() for node in nodes],
        "min_rs": minimum,
        "run_time_min": runtime,
        "critical_pair": pair,
        "all_eluted": all_eluted,
        "feasible": all_eluted
        and minimum >= target
        and (maximum is None or runtime <= maximum),
        "peaks": peaks,
    }


def ode_check(base, row):
    """Recompute each outlet with ODE and report numeric differences only."""
    method = base.model_copy(
        update={
            "gradient": [Node.model_validate(node) for node in row["gradient"]],
            "solver": "ode",
        }
    )
    rt_differences = []
    sigma_differences = []
    missing = []
    by_id = {peak["id"]: peak for peak in row["peaks"]}
    for compound in method.compounds:
        state = retention_state(method, compound)
        peak = by_id[compound.id]
        if state is None or peak["rt_min"] is None:
            if (state is None) != (peak["rt_min"] is None):
                missing.append(compound.id)
            continue
        width = band_width(method, compound, state, Program(method))["sigma_min"]
        rt_differences.append(abs(peak["rt_min"] / state.rt_min - 1))
        sigma_differences.append(abs(peak["sigma_min"] / width - 1))
    return {
        "max_rel_rt": max(rt_differences, default=None),
        "max_rel_sigma": max(sigma_differences, default=None),
        "elution_disagreements": missing,
        "solver": "ode",
    }


def search_warnings(base, nodes):
    """Aggregate source-condition warnings once using the search extent."""
    method = base.model_copy(update={"gradient": nodes})
    return list(
        dict.fromkeys(
            f"{compound.name}: {notice}"
            for compound in base.compounds
            for notice in parameter_warnings(method, compound)
        )
    )


def optimize_map(request):
    """Generate a bounded resolution cube with ranked and nondominated rows."""
    started = time.monotonic()
    base = prepare(request.simulation)
    axes = {
        key: np.linspace(
            getattr(request, key).min,
            getattr(request, key).max,
            getattr(request, key).steps,
        ).tolist()
        for key in ("gradient_time_min", "start_percent", "end_percent")
    }
    shape = (
        len(axes["start_percent"]),
        len(axes["end_percent"]),
        len(axes["gradient_time_min"]),
    )
    indices = []
    programs = []
    for start_index, start in enumerate(axes["start_percent"]):
        for end_index, end in enumerate(axes["end_percent"]):
            if end <= start + 1:
                continue
            for time_index, duration in enumerate(axes["gradient_time_min"]):
                indices.append((start_index, end_index, time_index))
                programs.append(
                    nodes_for(
                        base,
                        start,
                        [end],
                        [duration],
                        request.initial_hold_min,
                        request.final_hold_min,
                    )
                )
    if not programs:
        raise ValueError("No end > start + 1 combination in the grid")
    values = evaluate(base, programs)
    feasible = values["all_eluted"] & (values["min_rs"] >= request.target_rs)
    if request.max_run_time_min is not None:
        feasible &= values["run_time_min"] <= request.max_run_time_min
    runtimes = np.where(values["all_eluted"], values["run_time_min"], np.inf)
    ranking = sorted(
        range(len(programs)),
        key=lambda index: (
            not feasible[index],
            runtimes[index],
            -values["min_rs"][index],
        ),
    )
    cubes = {
        key: np.full(shape, None, dtype=object)
        for key in ("min_rs", "run_time", "all_eluted", "critical_pair")
    }
    for index, grid_index in enumerate(indices):
        all_eluted = bool(values["all_eluted"][index])
        cubes["all_eluted"][grid_index] = all_eluted
        if all_eluted:
            cubes["min_rs"][grid_index] = float(format(values["min_rs"][index], ".4g"))
            cubes["run_time"][grid_index] = float(f"{runtimes[index]:.4g}")
            order = values["order"][index]
            critical = values["critical"][index]
            cubes["critical_pair"][grid_index] = [
                base.compounds[int(order[critical + offset])].id for offset in (0, 1)
            ]
    top = [
        candidate(
            base,
            programs[index],
            values,
            index,
            request.target_rs,
            request.max_run_time_min,
        )
        for index in ranking[:10]
    ]
    for row in top:
        row["ode_check"] = ode_check(base, row)
    frontier = []
    highest_rs = -math.inf
    for index in sorted(
        np.flatnonzero(values["all_eluted"]),
        key=lambda index: (runtimes[index], -values["min_rs"][index]),
    ):
        if values["min_rs"][index] > highest_rs:
            frontier.append(index)
            highest_rs = values["min_rs"][index]
    if len(frontier) > 30:
        frontier = [
            frontier[index]
            for index in np.linspace(0, len(frontier) - 1, 30, dtype=int)
        ]
    extent = nodes_for(
        base,
        axes["start_percent"][0],
        [axes["end_percent"][-1]],
        [axes["gradient_time_min"][-1]],
        request.initial_hold_min,
        request.final_hold_min,
    )
    response = {
        "axes": axes,
        **{key: cube.tolist() for key, cube in cubes.items()},
        "top_candidates": top,
        "pareto": [
            candidate(
                base,
                programs[index],
                values,
                index,
                request.target_rs,
                request.max_run_time_min,
            )
            for index in frontier
        ],
        "evaluated": len(programs),
        "solver": "analytic",
        "elapsed_s": time.monotonic() - started,
        "warnings": search_warnings(base, extent),
    }
    if (
        len(
            json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode(
                "utf8"
            )
        )
        > 1048576
    ):
        raise ValueError(
            "Map response exceeds 1 MiB; reduce axis steps or compound ID length"
        )
    return response


def optimize_multisegment(request):
    """Search monotone ramps with differential evolution and a wall-clock budget."""
    started = time.monotonic()
    deadline = started + request.time_budget_s
    base = prepare(request.simulation)
    segments = request.segments
    start_min, start_max = request.start_percent_bounds
    end_min, end_max = request.end_percent_bounds
    start_max = min(start_max, end_max - 1.000001)
    bounds = (
        [(start_min, start_max), (0, 1)]
        + [(0, 1)] * (segments - 1)
        + [(0.001, 1)] * segments
        + [request.total_gradient_time_bounds]
    )
    stopped = False
    best_score = math.inf
    best_nodes = None
    evaluations = 0

    def decode(parameters):
        """Map sorted fractional knots and positive durations to monotone ramps."""
        start = float(parameters[0])
        end_lower = max(end_min, start + 1.000001)
        end = end_lower + float(parameters[1]) * (end_max - end_lower)
        fractions = np.r_[np.sort(parameters[2 : segments + 1]), 1.0]
        ends = start + (end - start) * fractions
        weights = np.asarray(parameters[segments + 1 : 2 * segments + 1])
        durations = weights / weights.sum() * parameters[-1]
        return nodes_for(
            base,
            start,
            ends,
            durations,
            request.initial_hold_min,
            request.final_hold_min,
        )

    def objective(parameters):
        """Score model calculations; stop extra evaluations after the deadline."""
        nonlocal evaluations, best_score, best_nodes, stopped
        if time.monotonic() >= deadline and best_nodes is not None:
            stopped = True
            return 1e12
        nodes = decode(parameters)
        values = evaluate(base, [nodes])
        evaluations += 1
        score = 1000 * max(0, request.target_rs - float(values["min_rs"][0])) + float(
            values["run_time_min"][0]
        )
        if not values["all_eluted"][0]:
            score += 1e6
        if request.max_run_time_min is not None:
            score += 1000 * max(
                0, float(values["run_time_min"][0]) - request.max_run_time_min
            )
        if score < best_score:
            best_score = score
            best_nodes = nodes
        return score

    def callback(parameters, convergence):
        """Stop between generations when the wall-clock budget is exhausted."""
        nonlocal stopped
        stopped = stopped or time.monotonic() >= deadline
        return stopped

    generator = np.random.default_rng(request.seed)
    population = generator.uniform(size=(max(5, 8 * len(bounds)), len(bounds)))
    lower = np.array([bound[0] for bound in bounds])
    upper = np.array([bound[1] for bound in bounds])
    population = lower + population * (upper - lower)
    if request.initial_candidate:
        nodes = request.initial_candidate
        start = float(np.clip(nodes[0].b_percent, start_min, start_max))
        end = float(
            np.clip(
                max(node.b_percent for node in nodes),
                max(end_min, start + 1.000001),
                end_max,
            )
        )
        end_lower = max(end_min, start + 1.000001)
        duration = float(
            np.clip(
                nodes[-1].time_min - request.initial_hold_min - request.final_hold_min,
                *request.total_gradient_time_bounds,
            )
        )
        population[0] = [
            start,
            (end - end_lower) / max(end_max - end_lower, 1e-12),
            *[index / segments for index in range(1, segments)],
            *([1.0] * segments),
            duration,
        ]
    fit = differential_evolution(
        objective,
        bounds,
        seed=request.seed,
        polish=False,
        callback=callback,
        init=population,
        maxiter=60,
        tol=0.001,
    )
    values = evaluate(base, [best_nodes])
    row = candidate(
        base, best_nodes, values, 0, request.target_rs, request.max_run_time_min
    )
    row["ode_check"] = ode_check(base, row)
    return {
        **row,
        "iterations": fit.nit,
        "evaluations": evaluations,
        "time_budget_stopped": stopped,
        "elapsed_s": time.monotonic() - started,
        "solver": "analytic",
        "warnings": search_warnings(base, best_nodes),
        "search_note": "Stochastic search within time budget; global optimality not claimed",
    }
