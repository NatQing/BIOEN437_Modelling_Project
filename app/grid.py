"""Common time grid, step-function sampling, ensemble mean and standard deviation."""
from dataclasses import dataclass

import numpy as np

from .gillespie import gillespie, make_rng


def make_grid(t_end, spacing):
    """Grid times t_j = j*spacing for j = 0 .. floor(T/spacing)."""
    m = int(np.floor(t_end / spacing + 1e-9))
    return np.arange(m + 1) * spacing


def sample_on_grid(times, counts, grid):
    """Value at t_j = count after the last firing at or before t_j. Returns (len(grid), n_species)."""
    idx = np.searchsorted(times, grid, side="right") - 1
    return counts[idx]


def mean_sd(samples):
    """Mean and sample SD (ddof=1) down the run axis of an (N, M+1) array. SD is 0 when N = 1."""
    mean = samples.mean(axis=0)
    if samples.shape[0] < 2:
        return mean, np.zeros_like(mean, dtype=float)
    return mean, samples.std(axis=0, ddof=1)


@dataclass
class Ensemble:
    species: list
    grid: np.ndarray
    runs: dict    # species -> (N, M+1) array
    mean: dict    # species -> (M+1,)
    sd: dict
    n_runs: int


def run_ensemble(model, t_end, spacing, n_runs, seed, progress=None):
    rng = make_rng(seed)
    grid = make_grid(t_end, spacing)
    arr = np.zeros((n_runs, len(model.species), len(grid)), dtype=np.int32)
    step = max(1, n_runs // 100)
    for i in range(n_runs):
        traj = gillespie(model, t_end, rng)
        arr[i] = sample_on_grid(traj.times, traj.counts, grid).T
        if progress is not None and ((i + 1) % step == 0 or i + 1 == n_runs):
            progress(i + 1, n_runs)
    runs, mean, sd = {}, {}, {}
    for s_idx, s in enumerate(model.species):
        runs[s] = arr[:, s_idx, :]
        mean[s], sd[s] = mean_sd(runs[s])
    return Ensemble(list(model.species), grid, runs, mean, sd, n_runs)
