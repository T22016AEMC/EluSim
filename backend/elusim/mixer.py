"""Independent well-mixed tank integration; no external simulator code."""

import numpy as np
from scipy.integrate import solve_ivp


def mixed_profile(program, mixer_ml):
    """Preintegrate dphi/dt=F(t)/Vmixer*(phi_pump-phi).

    A mass balance for one ideal stirred tank (Levenspiel, Chemical Reaction
    Engineering, 3rd ed., Wiley, 1999). Tank mean delay is additional to the
    existing pure-volume dwell translation, which remains in Program.local_phi.
    Split at every program knot so step jumps never straddle an integration
    interval. The interpolation grid is at most 0.002 min apart.
    """
    times = [0.0]
    values = [program.composition(0)]
    current = values[0]
    for index, (start, end) in enumerate(zip(program.t[:-1], program.t[1:])):
        grid = np.linspace(start, end, max(2, int(np.ceil((end-start)/0.002))+1))

        def derivative(time_min, state):
            """Use the segment left limit at a discontinuous terminal knot."""
            phi = (program.phi[index] if program.step[index]
                   else float(np.interp(time_min, program.t, program.phi)))
            return [program.flow(time_min) / mixer_ml * (phi - state[0])]

        solution = solve_ivp(
            derivative, (start, end), [current], method="Radau",
            t_eval=grid, rtol=1e-9, atol=1e-11,
        )
        if not solution.success:
            raise ValueError("混合器積分失敗")
        times.extend(grid[1:].tolist())
        values.extend(solution.y[0, 1:].tolist())
        current = float(solution.y[0, -1])
    return np.asarray(times), np.asarray(values)
