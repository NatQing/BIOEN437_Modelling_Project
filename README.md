# Stochastic Simulation Platform for Biologists (BIOEN437)

A static website that simulates mass-action reaction models with the Gillespie direct method.
Python runs in the browser (Pyodide, in a Web Worker); nothing is installed and no server is used.

**Features:** model text box with line-numbered errors, example models, file upload, single run (step plot),
ensemble (mean ± 1 SD, optional overlaid runs), seed control, CSV download, Antimony export, and the
V1–V3 validation tests runnable in the page.

Model language: see [docs/SPECIFICATION.md](docs/SPECIFICATION.md). Reactions may have any number of reactant
molecules (propensity = k × product of C(count, stoichiometry)).

## Layout
- `index.html`, `static/` – page, worker, styles
- `app/` – `parser`, `model`, `gillespie`, `grid`, `export`, `plotting`, plus `validation` and `service` (browser glue)
- `tests/` – pytest suite (unit tests, V1–V3)
- `reference/` – `generate_reference.py` and the saved Tellurium output used by V2
- `docs/` – specification

## Run locally
```bash
pip install numpy matplotlib seaborn pytest tellurium
pytest -q
python -m http.server 8000   # then open http://localhost:8000
```

## Regenerate the Tellurium reference (V2)
```bash
python reference/generate_reference.py
```

## Deploy
Settings → Pages → Source: **GitHub Actions**. `.github/workflows/pages.yml` publishes on every push to `main`;
`ci.yml` runs pytest.
