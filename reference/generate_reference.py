"""Generate the Tellurium reference data used by validation test V2.

Run offline (Tellurium cannot run in the browser):
    pip install tellurium numpy
    python reference/generate_reference.py

It exports the Section 2 example model to Antimony with our own exporter, runs 500 Gillespie
simulations with Tellurium (r.gillespie) on that exported text, puts them on the same time
grid, and saves means and SDs to reference/tellurium_reference.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tellurium as te  # noqa: E402

from app.examples import SPEC_EXAMPLE  # noqa: E402
from app.export import to_antimony  # noqa: E402
from app.parser import parse_model  # noqa: E402

N_RUNS = 500
T_END = 10.0
SPACING = 1.0


def main():
    model = parse_model(SPEC_EXAMPLE)
    antimony = to_antimony(model)
    r = te.loada(antimony)
    free = [s for s in model.species if s not in model.boundary]
    r.selections = ["time"] + free
    points = int(round(T_END / SPACING)) + 1
    runs = np.zeros((N_RUNS, len(free), points))
    for i in range(N_RUNS):
        r.reset()
        r.integrator = "gillespie"
        r.integrator.seed = 1000 + i
        res = r.simulate(0, T_END, points)
        runs[i] = np.array(res)[:, 1:].T
    out = {
        "tellurium_version": te.__version__,
        "antimony": antimony,
        "n_runs": N_RUNS,
        "t_end": T_END,
        "spacing": SPACING,
        "grid": [j * SPACING for j in range(points)],
        "species": free,
        "mean": {s: runs[:, k, :].mean(axis=0).tolist() for k, s in enumerate(free)},
        "sd": {s: runs[:, k, :].std(axis=0, ddof=1).tolist() for k, s in enumerate(free)},
    }
    path = ROOT / "reference" / "tellurium_reference.json"
    path.write_text(json.dumps(out, indent=1))
    print("wrote", path)


if __name__ == "__main__":
    main()
