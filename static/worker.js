// Runs Python (Pyodide) off the main thread so the page stays responsive.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");

const FILES = ["__init__", "model", "parser", "gillespie", "grid", "export", "plotting", "examples", "validation", "service"];
let service = null;

const ready = (async () => {
  const pyodide = await loadPyodide();
  await pyodide.loadPackage(["numpy", "matplotlib"]);
  try { await pyodide.loadPackage("seaborn"); } catch (e) { /* optional: only changes plot style */ }
  pyodide.FS.mkdirTree("/home/pyodide/app");
  for (const f of FILES) {
    const src = await (await fetch(new URL(`../app/${f}.py`, self.location))).text();
    pyodide.FS.writeFile(`/home/pyodide/app/${f}.py`, src);
  }
  pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
  service = pyodide.pyimport("app.service");
  postMessage({ type: "ready" });
})();

onmessage = async (e) => {
  const { id, fn, args } = e.data;
  try {
    await ready;
    let result;
    if (fn === "validation") {
      const ref = await fetch(new URL("../reference/tellurium_reference.json", self.location));
      result = service.run_validation(ref.ok ? await ref.text() : "");
    } else if (fn === "run_ensemble") {
      const progress = (done, total) => postMessage({ type: "progress", id, done, total });
      result = service.run_ensemble_json(...args, progress);
    } else {
      result = service[fn](...args);
    }
    postMessage({ type: "result", id, result });
  } catch (err) {
    postMessage({ type: "result", id, result: JSON.stringify({ ok: false, error: String(err) }) });
  }
};
