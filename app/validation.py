"""Validation checks V1-V3. Used by pytest and by the Validation button in the site."""
from dataclasses import dataclass
from math import sqrt

import numpy as np

from .examples import BIRTH_DEATH, SPEC_EXAMPLE
from .gillespie import gillespie, make_rng
from .grid import run_ensemble
from .parser import parse_model
from .plotting import plot_histogram


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    figure: object = None  # optional matplotlib figure


def check_v1(n_runs=1000, t_end=20.0, seed=2024):
    """Birth-death steady state: Poisson, so mean = k1/k2 and variance/mean = 1."""
    model = parse_model(BIRTH_DEATH)
    k1, k2 = model.constants["k1"], model.constants["k2"]
    ens = run_ensemble(model, t_end, t_end, n_runs, seed)
    final = ens.runs["A"][:, -1].astype(float)
    mean, var = final.mean(), final.var(ddof=1)
    expected = k1 / k2
    mean_tol = 3 * sqrt(expected / n_runs)           # 3 standard errors of the mean
    ratio_tol = 3 * sqrt(2 / (n_runs - 1))           # 3 standard errors of a variance ratio
    ok_mean = abs(mean - expected) <= mean_tol
    ok_ratio = abs(var / mean - 1) <= ratio_tol
    detail = (f"mean = {mean:.3f} (expected {expected:g} +/- {mean_tol:.3f}); "
              f"variance/mean = {var / mean:.3f} (expected 1 +/- {ratio_tol:.3f}); {n_runs} runs")
    fig = plot_histogram(final, "V1: final A vs Poisson", poisson_mean=expected)
    return CheckResult("V1 steady-state spread (birth-death)", ok_mean and ok_ratio, detail, fig)


def check_v2(reference, n_runs=None, seed=7):
    """Our gridded mean/SD against saved Tellurium output for the exported model."""
    if reference is None:
        return CheckResult("V2 vs Tellurium", False, "reference/tellurium_reference.json is missing")
    model = parse_model(SPEC_EXAMPLE)
    n = n_runs or reference["n_runs"]
    ens = run_ensemble(model, reference["t_end"], reference["spacing"], n, seed)
    n_ref = reference["n_runs"]
    zs = []
    for s in reference["species"]:
        for kind, ours, theirs in (("mean", ens.mean[s], np.array(reference["mean"][s])),
                                   ("sd", ens.sd[s], np.array(reference["sd"][s]))):
            if kind == "mean":
                se = np.sqrt(ens.sd[s] ** 2 / n + np.array(reference["sd"][s]) ** 2 / n_ref)
            else:  # standard error of an SD is about sd / sqrt(2(N-1))
                se = np.sqrt(ens.sd[s] ** 2 / (2 * (n - 1)) + theirs ** 2 / (2 * (n_ref - 1)))
            diff = np.abs(ours - theirs)
            z = np.where(se > 0, diff / np.where(se > 0, se, 1), np.where(diff > 1e-9, np.inf, 0.0))
            zs.append(z)
    z = np.concatenate(zs)
    worst = float(z.max())
    frac3 = float((z > 3).mean())
    ok = worst < 4 and frac3 < 0.05
    detail = (f"{n} runs here vs {n_ref} Tellurium runs ({reference.get('tellurium_version', '?')}); "
              f"largest difference = {worst:.2f} standard errors; {100 * frac3:.1f}% of {z.size} "
              f"comparisons beyond 3 SE (pass: max < 4 and < 5% beyond 3)")
    return CheckResult("V2 vs Tellurium (6 reactions, 500 runs)", ok, detail)


def check_v3(seed=123):
    """Same seed gives identical output; different seeds do not."""
    model = parse_model(SPEC_EXAMPLE)
    a = gillespie(model, 5.0, make_rng(seed))
    b = gillespie(model, 5.0, make_rng(seed))
    c = gillespie(model, 5.0, make_rng(seed + 1))
    same = np.array_equal(a.times, b.times) and np.array_equal(a.counts, b.counts)
    differ = not (a.times.shape == c.times.shape and np.array_equal(a.times, c.times))
    return CheckResult("V3 seed reproducibility", same and differ,
                       f"same seed identical: {same}; different seed differs: {differ}")
