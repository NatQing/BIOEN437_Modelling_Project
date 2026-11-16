# **Specification: Stochastic Simulation Platform for Biologists**

**Team:** Yi Nathen Qing, Chris Soetedjo; **Track:** Undergraduate

*For Claude: Instructions to the implementing AI agent: build exactly what this document describes. Follow the milestones in order, write the listed tests at each milestone, and do not move on until they pass. Do not add features not listed here. Prefer simple, readable code the team can explain line by line.*

## **1\. What the platform does**

A static website (GitHub Pages). The user opens the URL and sees a text box for a reaction model and a panel of options (end time, seed, number of runs N, grid spacing, species to plot). They enter a model, press **Run**, see a progress bar or a clear error message (with line number), and then see the simulated graphs. They can download results as CSV and export the model as Antimony. Nothing needs installing. Models are all run on the local host.

## **2\. Model language**

Same text format as Tellurium's Antimony, restricted to mass-action reactions with integer molecule counts.

```
# comment (also // comment)
J1: A + B -> C; k1
J2: C -> A + B; k2
J3: 2 A -> D; k3
J4: -> A; k4
J5: D -> ; k5
$X -> A; k6
species A, B, C, D        # optional declarations
const species $X
A = 100; B = 50; C = 0; D = 0; X = 10
k1 = 0.001; k2 = 0.1; k3 = 0.0005; k4 = 2; k5 = 0.05; k6 = 0.2
```

Rules:

* Statements are separated by newlines or `;`. Comments start with `#` or `//`.  
* Reaction: `[name:] reactants -> products; rate`. Either side may be empty. `=>` is accepted as `->`. Unnamed reactions are numbered J1, J2, ... in order. Stoichiometry is a positive integer before a species.&nbsp;  
* `$` prefix or `const species` marks a boundary species: used in propensities, never changes.  
* `species`/`var species` declarations are optional. Undeclared species used in reactions are accepted.  
* Every species (non-negative integer) and every rate constant (number ≥ 0\) must have a value. Missing: `Line n: no value given for 'X'`. Any other bad line: `Line n: syntax error: <text>`.  
* The rate field is either a bare constant (`k1`), which the platform treats as mass action, or the explicit mass-action expression Tellurium would need (`k1*A*B`, `k3*A*(A-1)/2`). Any other expression is an error.  
* Propensities: `-> ...`: k. `A -> ...`: k·A. `A + B -> ...`: k·A·B. `2 A -> ...`: k·A·(A−1)/2.  
* **Tellurium caveat:** in Tellurium a bare `k1` means the rate is exactly k1, not mass action. So the Antimony export always writes explicit mass-action expressions (`J1: A + B -> C; k1*A*B`, `J3: 2 A -> D; k3*A*(A-1)/2`), and Tellurium comparisons always use exported text.  
* Not supported: other functions, compartments, units, reversible arrows.

## **3\. Gillespie direct method (implemented from scratch)**

1. Start with the initial molecule counts at t \= 0\.  
2. Compute the propensity a\_j of every reaction from the current counts; a₀ \= Σ a\_j.  
3. If a₀ \= 0, nothing more can happen: stop and hold the state to the end time.  
4. **Random number r₁ (uniform on (0,1)) gives the waiting time:** Δt \= −ln(r₁) / a₀. If t \+ Δt exceeds the end time, stop.  
5. **Random number r₂ (uniform on (0,1)) picks the reaction:** compute r₂·a₀ and choose the first reaction j whose cumulative propensity a₁ \+ … \+ a\_j is ≥ r₂·a₀ (so reaction j is chosen with probability a\_j / a₀).  
6. Apply reaction j's stoichiometry to the counts (skip boundary species), set t ← t \+ Δt, record (t, counts), return to step 2\.

Only the uniform random number generator (NumPy `Generator`, seeded by the user) and `log` come from libraries. The loop itself is our own code. Output: the list of (time, counts) at every firing, starting with t \= 0\.

## **4\. Time grid, ensemble mean and standard deviation**

Runs fire at different times, so each is put on a common grid first. The user sets the end time T and spacing Δ; grid times are t\_j \= jΔ, j \= 0…⌊T/Δ⌋. For each run, the value of a species at t\_j is its count after the last firing at or before t\_j (step-function sampling; vectorised with `np.searchsorted(times, grid, side="right") - 1`). This yields an N × (M+1) array per species. The ensemble mean and standard deviation (sample SD, `ddof=1`) are computed down the run axis at every grid point.

## **5\. User interface**

* **Left:** model text box, file upload, example-model dropdown, error messages.  
* **Options:** end time, seed (blank \= random; the seed used is shown), N, grid spacing, species checklist, "overlay individual runs" toggle.  
* **Buttons:** Run once, Run ensemble, Download CSV, Export Antimony, Validation tests.  
* **Right:** plots and progress bar. Single run: step plot (`drawstyle="steps-post"`), never smoothed lines. Ensemble: mean line with shaded ±1 SD band, optional overlaid runs.  
* **CSV:** single run: `time, A, B, ...`, one row per firing. Ensemble: `time, A_mean, A_sd, ...`, one row per grid point.

## **6\. Validation plan**

Tests live in `tests/`, run automatically with `pytest` (GitHub Actions) and from the Validation button in the site. Tellurium is the reference.

* **Unit tests:** parser (example loads, broken inputs give correct line numbers, missing values reported); propensity values for all four forms; stoichiometry matrix and boundary species; grid sampling on a hand-made trajectory, including a firing exactly on a grid point.  
* **V1 steady-state spread:** birth-death model `-> A; k1` / `A -> ; k2` \[confirm V1 model with instructor\]. 1000 runs, long time, histogram of final A. Check variance/mean ≈ 1 (within a few percent) and mean ≈ k1/k2.  
* **V2 vs Tellurium:** a model with ≥ 3 reactions. 500 runs here and 500 with `r.gillespie()` on our exported Antimony. Compare gridded means and SDs; they must agree within sampling noise (e.g. differences within \~3 standard errors). Tellurium cannot run in the browser, so a script in `reference/` generates its output offline and the site compares against that saved file.  
* **V3 seed:** same seed gives identical output; different seeds do not.

## **7\. Language and framework**

**Python.** It is the easiest language for the team, so we can understand and explain every line. NumPy lets us vectorise the gridding and the ensemble statistics. Tellurium is itself a Python package, so the reference comparison needs no translation. LLM assistants are strongest in Python, which makes AI-assisted development more reliable. \[Team: add anything else.\]

**Framework:** a static site on GitHub Pages running the Python code in the browser with **Pyodide** (Python compiled to WebAssembly, includes NumPy and Matplotlib), inside a Web Worker so the page stays responsive and can show a progress bar. Plain HTML/JS for the page. Matplotlib draws the plots. No server. Same Python package is tested natively with `pytest`.

Repo layout: `index.html`, `app/` (parser, model, gillespie, grid, export, plotting), `tests/`, `reference/` (Tellurium reference data and generating script), `docs/`.

## **8\. Who does what**

- Nathen: Ideation and innovation for backend  
- Chris: Front-end development (UI). Brainstorming for back-end  
- Claude: Programming

## **9\. Milestones and tests**

| Week | Deliverable | Tests that must pass |
| :---- | :---- | :---- |
| 5 | Parser, line-numbered errors, bare site deployed on GitHub Pages | Section 2 example loads; three broken inputs give correct errors; missing-symbol error |
| 6 | Single Gillespie run, step plot, CSV out | Propensity and stoichiometry unit tests; CSV has one row per firing; plot is stepped |
| 7 | Ensemble, grid, mean ± SD plot, seed control, grid CSV | Grid unit tests; V3 seed test; deterministic-model sanity check (SD \= 0\) |
| 8 | Antimony export | Export loads in Tellurium and gives matching mass-action dynamics; V1 passes |
| 9 | V1–V3 runnable in the site | All validation tests pass in CI and in the browser |
| 10 | Code freeze, final report, usability pass | A non-programmer completes a run without help; bad input (N \= 10,000, missing values) handled gracefully |

&nbsp;
