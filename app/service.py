"""JSON-friendly entry points called from the browser (Pyodide) worker."""
import base64
import json

from .export import ensemble_csv, single_run_csv, to_antimony
from .gillespie import SimulationError, gillespie, make_rng
from .grid import make_grid, run_ensemble
from .parser import ParseError, parse_model
from .plotting import fig_to_png, plot_ensemble, plot_single
from . import validation

MAX_RUNS = 10_000
MAX_CELLS = 40_000_000   # runs x species x grid points


def _png(fig):
    return base64.b64encode(fig_to_png(fig)).decode("ascii")


def _fail(message, line=None):
    return json.dumps({"ok": False, "error": message, "line": line})


def check_model(text):
    try:
        m = parse_model(text)
    except ParseError as e:
        return _fail(str(e), e.line)
    return json.dumps({"ok": True, "species": m.species, "reactions": len(m.reactions)})


def _resolve_seed(seed):
    if seed is None or seed == "":
        import secrets
        return secrets.randbits(32)
    seed = int(seed)
    if seed < 0:
        raise ValueError("seed must be a non-negative integer")
    return seed


def _plot_list(model, species):
    if hasattr(species, "to_py"):  # a JavaScript array arriving from Pyodide
        species = species.to_py()
    chosen = [s for s in (species or []) if s in model.species]
    return chosen or [s for s in model.species if s not in model.boundary] or list(model.species)


def run_once(text, t_end, seed, species):
    try:
        model = parse_model(text)
        t_end = float(t_end)
        if not t_end > 0:
            return _fail("End time must be greater than 0.")
        seed = _resolve_seed(seed)
        traj = gillespie(model, t_end, make_rng(seed))
    except ParseError as e:
        return _fail(str(e), e.line)
    except (SimulationError, ValueError) as e:
        return _fail(str(e))
    fig = plot_single(traj, _plot_list(model, species), t_end)
    return json.dumps({"ok": True, "png": _png(fig), "csv": single_run_csv(traj), "seed": seed,
                       "info": f"{len(traj.times) - 1} reaction events"})


def run_ensemble_json(text, t_end, spacing, n_runs, seed, species, overlay, progress=None):
    try:
        model = parse_model(text)
        t_end, spacing = float(t_end), float(spacing)
        if not t_end > 0:
            return _fail("End time must be greater than 0.")
        if not spacing > 0 or spacing > t_end:
            return _fail("Grid spacing must be greater than 0 and no larger than the end time.")
        if float(n_runs) != int(float(n_runs)) or int(float(n_runs)) < 1:
            return _fail("N must be a whole number of at least 1.")
        n_runs = int(float(n_runs))
        if n_runs > MAX_RUNS:
            return _fail(f"N = {n_runs:,} is too large; the limit is {MAX_RUNS:,} runs.")
        cells = n_runs * len(model.species) * len(make_grid(t_end, spacing))
        if cells > MAX_CELLS:
            return _fail("N x grid points is too large for the browser. Reduce N or increase the grid spacing.")
        seed = _resolve_seed(seed)
        ens = run_ensemble(model, t_end, spacing, n_runs, seed, progress)
    except ParseError as e:
        return _fail(str(e), e.line)
    except (SimulationError, ValueError) as e:
        return _fail(str(e))
    fig = plot_ensemble(ens, _plot_list(model, species), bool(overlay))
    return json.dumps({"ok": True, "png": _png(fig), "csv": ensemble_csv(ens), "seed": seed,
                       "info": f"{n_runs} runs on {len(ens.grid)} grid points"})


def export_antimony(text):
    try:
        return json.dumps({"ok": True, "text": to_antimony(parse_model(text))})
    except ParseError as e:
        return _fail(str(e), e.line)


def run_validation(reference_text):
    reference = json.loads(reference_text) if reference_text else None
    results = [validation.check_v1(), validation.check_v2(reference), validation.check_v3()]
    return json.dumps([
        {"name": r.name, "passed": bool(r.passed), "detail": r.detail,
         "png": _png(r.figure) if r.figure is not None else None}
        for r in results])
