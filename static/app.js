import { EXAMPLES } from "./examples.js";

const $ = (id) => document.getElementById(id);
const worker = new Worker("static/worker.js");
let nextId = 1;
const pending = new Map();
let lastCsv = null, lastCsvName = "results.csv";
let busy = false;

worker.onmessage = (e) => {
  const m = e.data;
  if (m.type === "ready") {
    $("status").textContent = "Ready";
    setButtons(true);
    checkModel();
  } else if (m.type === "progress") {
    $("progress").hidden = false;
    $("progress").value = (100 * m.done) / m.total;
    $("info").textContent = `Run ${m.done} of ${m.total}`;
  } else if (m.type === "result") {
    const p = pending.get(m.id);
    pending.delete(m.id);
    p(JSON.parse(m.result));
  }
};

function call(fn, args) {
  return new Promise((resolve) => {
    const id = nextId++;
    pending.set(id, resolve);
    worker.postMessage({ id, fn, args });
  });
}

function setButtons(on) {
  for (const id of ["run-once", "run-ens", "export", "validate"]) $(id).disabled = !on;
  $("dl-csv").disabled = !on || lastCsv === null;
}

function showError(msg) {
  $("error").hidden = !msg;
  $("error").textContent = msg || "";
}

function download(name, text, type = "text/csv") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- model editing ----
let checkTimer = null, checkToken = 0;
function checkModelSoon() { clearTimeout(checkTimer); checkTimer = setTimeout(checkModel, 400); }

async function checkModel() {
  const token = ++checkToken;
  const r = await call("check_model", [$("model").value]);
  if (token !== checkToken) return;
  showError(r.ok ? "" : r.error);
  if (r.ok) renderSpecies(r.species);
}

function renderSpecies(species) {
  const had = new Set([...document.querySelectorAll("#species input:checked")].map((c) => c.value));
  const first = document.querySelectorAll("#species input").length === 0;
  $("species").innerHTML = "";
  for (const s of species) {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox"; box.value = s; box.checked = first || had.has(s);
    label.append(box, " " + s);
    $("species").append(label);
  }
}

const selectedSpecies = () => [...document.querySelectorAll("#species input:checked")].map((c) => c.value);

function loadExample(name) {
  const ex = EXAMPLES[name];
  $("model").value = ex.text;
  $("tend").value = ex.T;
  $("dt").value = ex.dt;
  $("species").innerHTML = "";
  checkModel();
}

for (const name of Object.keys(EXAMPLES)) $("example").add(new Option(name, name));
$("example").onchange = () => loadExample($("example").value);
$("model").oninput = checkModelSoon;
$("upload").onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  $("model").value = await f.text();
  $("species").innerHTML = "";
  checkModel();
  e.target.value = "";
};

// ---- running ----
function showImage(r) {
  $("output").innerHTML = "";
  const img = new Image();
  img.src = "data:image/png;base64," + r.png;
  img.alt = "Simulation plot";
  $("output").append(img);
}

async function withBusy(fn) {
  if (busy) return;
  busy = true; setButtons(false);
  $("progress").hidden = true; $("progress").value = 0;
  try { await fn(); } finally { busy = false; setButtons(true); $("progress").hidden = true; }
}

function finish(r, csvName) {
  if (!r.ok) { showError(r.error); $("info").textContent = ""; return; }
  showError("");
  lastCsv = r.csv; lastCsvName = csvName;
  showImage(r);
  $("seed").placeholder = `random (used ${r.seed})`;
  $("info").textContent = `Seed used: ${r.seed}. ${r.info}.`;
}

$("run-once").onclick = () => withBusy(async () => {
  $("info").textContent = "Running…";
  finish(await call("run_once", [$("model").value, $("tend").value, $("seed").value, selectedSpecies()]), "single_run.csv");
});

$("run-ens").onclick = () => withBusy(async () => {
  const n = Number($("nruns").value);
  if (n > 2000 && !confirm(`${n.toLocaleString()} runs may take a while in the browser. Continue?`)) return;
  $("info").textContent = "Running…";
  finish(await call("run_ensemble", [$("model").value, $("tend").value, $("dt").value, $("nruns").value,
    $("seed").value, selectedSpecies(), $("overlay").checked]), "ensemble.csv");
});

$("dl-csv").onclick = () => lastCsv && download(lastCsvName, lastCsv);

$("export").onclick = () => withBusy(async () => {
  const r = await call("export_antimony", [$("model").value]);
  if (!r.ok) return showError(r.error);
  showError("");
  download("model.ant", r.text, "text/plain");
});

$("validate").onclick = () => withBusy(async () => {
  $("info").textContent = "Running validation tests… (about 10 seconds)";
  const results = await call("validation", []);
  $("info").textContent = "";
  $("output").innerHTML = "";
  for (const t of results) {
    const div = document.createElement("div");
    div.className = "test";
    const head = document.createElement("div");
    head.innerHTML = `<span class="${t.passed ? "pass" : "fail"}">${t.passed ? "PASS" : "FAIL"}</span> `;
    head.append(t.name);
    const detail = document.createElement("div");
    detail.className = "hint"; detail.textContent = t.detail;
    div.append(head, detail);
    if (t.png) { const img = new Image(); img.src = "data:image/png;base64," + t.png; img.style.maxWidth = "100%"; div.append(img); }
    $("output").append(div);
  }
});

setButtons(false);
loadExample(Object.keys(EXAMPLES)[0]);
