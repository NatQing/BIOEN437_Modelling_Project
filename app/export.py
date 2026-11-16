"""Exports: Antimony text (explicit mass-action rates) and CSV."""
from .model import mass_action_text


def _num(x):
    return repr(float(x)) if not float(x).is_integer() else str(int(x)) if abs(x) < 1e15 else repr(float(x))


def to_antimony(model):
    """Antimony text for Tellurium. Rates are always explicit (k1*A*B), because a bare k1 is not mass action there."""
    lines = ["# Exported from the BIOEN437 stochastic simulation platform"]
    for r in model.reactions:
        left = " + ".join((f"{n} {s}" if n > 1 else s) for s, n in r.reactants.items())
        right = " + ".join((f"{n} {s}" if n > 1 else s) for s, n in r.products.items())
        body = f"{left} -> {right}".replace("  ", " ").strip()
        lines.append(f"{r.name}: {body}; {mass_action_text(r.rate_name, r.reactants)}")
    free = [s for s in model.species if s not in model.boundary]
    fixed = [s for s in model.species if s in model.boundary]
    if free:
        lines.append("species " + ", ".join(free))
    if fixed:
        lines.append("const species " + ", ".join(fixed))
    for s in model.species:
        lines.append(f"{s} = {model.initial[s]}")
    for k, v in model.constants.items():
        lines.append(f"{k} = {_num(v)}")
    return "\n".join(lines) + "\n"


def single_run_csv(traj):
    """time, A, B, ...: one row per firing (plus the t = 0 row)."""
    rows = ["time," + ",".join(traj.species)]
    for t, row in zip(traj.times, traj.counts):
        rows.append(repr(float(t)) + "," + ",".join(str(int(v)) for v in row))
    return "\n".join(rows) + "\n"


def ensemble_csv(ens):
    """time, A_mean, A_sd, ...: one row per grid point."""
    head = ["time"]
    for s in ens.species:
        head += [f"{s}_mean", f"{s}_sd"]
    rows = [",".join(head)]
    for j, t in enumerate(ens.grid):
        cells = [repr(float(t))]
        for s in ens.species:
            cells += [repr(float(ens.mean[s][j])), repr(float(ens.sd[s][j]))]
        rows.append(",".join(cells))
    return "\n".join(rows) + "\n"
