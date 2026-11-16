"""Gillespie direct method, written from scratch.
Only the uniform random generator (NumPy) and log come from libraries."""
from dataclasses import dataclass
from math import log

import numpy as np

from .model import propensity


class SimulationError(RuntimeError):
    pass


@dataclass
class Trajectory:
    species: list
    times: np.ndarray    # shape (n_events + 1,), starts at 0
    counts: np.ndarray   # shape (n_events + 1, n_species), integer


def make_rng(seed):
    return np.random.default_rng(seed)


def _uniform(rng):
    """Uniform on the open interval (0, 1): redraw if the generator returns exactly 0."""
    r = rng.random()
    while r == 0.0:
        r = rng.random()
    return r


def gillespie(model, t_end, rng, max_events=1_000_000):
    compiled = model.compile()
    counts = model.initial_counts()
    t = 0.0
    times = [0.0]
    states = [list(counts)]

    while True:
        # step 2: propensities and their sum
        a = [propensity(k, pairs, counts) for k, pairs, _ in compiled]
        a0 = sum(a)
        # step 3: nothing can happen any more
        if a0 <= 0:
            break
        # step 4: waiting time
        r1 = _uniform(rng)
        dt = -log(r1) / a0
        if t + dt > t_end:
            break
        # step 5: choose the reaction
        target = _uniform(rng) * a0
        cumulative = 0.0
        chosen = None
        for j, aj in enumerate(a):
            cumulative += aj
            if cumulative >= target:
                chosen = j
                break
        if chosen is None:  # rounding: fall back to the last reaction that can fire
            chosen = max(j for j, aj in enumerate(a) if aj > 0)
        # step 6: apply, advance time, record
        for i, delta in compiled[chosen][2]:
            counts[i] += delta
        t += dt
        times.append(t)
        states.append(list(counts))
        if len(times) > max_events:
            raise SimulationError(
                f"More than {max_events:,} reaction events in one run; reduce the end time or the rates.")

    return Trajectory(list(model.species), np.array(times), np.array(states, dtype=np.int64))
