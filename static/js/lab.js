// Laboratório: execução real dos algoritmos sobre vetores, com passos, pseudocódigo e verificação.
import {
  ApiError, Player, SCENARIO_TYPE, announce, api, clear, download, el, fmt, fmtMs, isAbort, readInt, readJsonFile,
  renderPseudocode, scenarioTools, setBusy, showError, svg,
} from "./core.js";
import { algorithmById, getCatalog } from "./catalog.js";

const $ = (id) => document.getElementById(id);
const W = 800;
const H = 360;
const PAD = 24;
export const PIVOT_LABELS = {
  ultimo: "Último elemento",
  mediana3: "Mediana de 3",
  aleatorio: "Aleatório (seed)",
  mediana_medianas: "Mediana das medianas",
};
const KIND_LABELS = {
  base: "Caso-base", divide: "Dividir", merge: "Intercalar", combine: "Combinar", pivot: "Pivô", partition: "Partição",
};

let catalog = null;
let algorithm = "merge_sort";
let result = null;
let player = null;
let latestRun = 0;

function parseValues(text) {
  const parts = text.split(/[\s,;]+/).filter(Boolean);
  const values = parts.map(Number);
  if (!values.length || values.length > 2000 || !values.every((v) => Number.isInteger(v) && Math.abs(v) <= 1e9)) {
    throw new ApiError("Valores: informe de 1 a 2.000 inteiros (até 10⁹ em módulo), separados por vírgula.");
  }
  return values;
}

function syncControls() {
  const custom = $("lab-mode").value === "custom";
  document.querySelectorAll(".lab-scenario").forEach((node) => { node.hidden = custom; });
  document.querySelectorAll(".lab-custom").forEach((node) => { node.hidden = !custom; });
  const pivots = catalog.pivots[algorithm];
  document.querySelector(".lab-pivot").hidden = !pivots;
  document.querySelector(".lab-k").hidden = algorithm !== "quickselect";
  if (pivots) {
    const previous = $("lab-pivot").value;
    $("lab-pivot").replaceChildren(...pivots.map((p) => el("option", { value: p, text: PIVOT_LABELS[p] })));
    $("lab-pivot").value = pivots.includes(previous) ? previous : pivots[0];
  }
  document.querySelectorAll("#lab-algorithms button").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.id === algorithm));
  });
  renderTheory();
}

function renderTheory() {
  const info = algorithmById(catalog, algorithm);
  clear($("lab-theory")).append(
    el("h3", { text: info.name }),
    el("p", { text: info.problem }),
    el("dl", { class: "kv" },
      el("dt", { text: "Dividir" }), el("dd", { text: info.divide }),
      el("dt", { text: "Conquistar" }), el("dd", { text: info.conquer }),
      el("dt", { text: "Combinar" }), el("dd", { text: info.combine }),
      el("dt", { text: "Caso-base" }), el("dd", { text: info.base_case }),
      el("dt", { text: "Recorrência" }), el("dd", { text: info.recurrence }),
      el("dt", { text: "Pior caso" }), el("dd", { text: info.complexity.worst }),
      el("dt", { text: "Referência" }), el("dd", { text: info.reference })),
    el("p", { class: "small" }, el("a", { href: `#teoria?alg=${algorithm}`, text: "Teoria completa →" })),
  );
  renderPseudocode($("lab-pseudo"), info.pseudocode, null);
}

async function run() {
  const form = $("lab-form");
  showError($("lab-error"), null);
  let body;
  try {
    body = { algorithm, seed: readInt($("lab-seed"), "Seed"), params: {} };
    if ($("lab-mode").value === "custom") {
      try {
        body.values = parseValues($("lab-values").value);
        $("lab-values").setAttribute("aria-invalid", "false");
      } catch (error) {
        $("lab-values").setAttribute("aria-invalid", "true");
        throw error;
      }
    } else {
      body.scenario = $("lab-scenario").value;
      body.n = readInt($("lab-n"), "n");
    }
    if (catalog.pivots[algorithm]) body.params.pivot = $("lab-pivot").value;
    if (algorithm === "quickselect") {
      const n = body.values ? body.values.length : body.n;
      $("lab-k").max = String(n);
      body.params.k = readInt($("lab-k"), "k");
    }
  } catch (error) {
    showError($("lab-error"), error);
    return;
  }
  const runId = ++latestRun;
  setBusy(form, true);
  try {
    result = await api("/api/lab/run", { method: "POST", body, key: "lab" });
    renderSummary();
    player.load(result.steps.length);
    if (!result.steps.length) drawStatic();
    announce(`${algorithmById(catalog, algorithm).name}: ${result.verification.ok ? "resultado confere" : "resultado diverge"} da referência.`);
  } catch (error) {
    if (!isAbort(error)) showError($("lab-error"), error);
  } finally {
    // Uma execução cancelada não pode liberar o botão enquanto a mais nova ainda roda.
    if (runId === latestRun) setBusy(form, false);
  }
}

function outputText() {
  const out = result.output;
  if (algorithm === "quickselect") return `${result.params.k}º menor = ${out}`;
  if (algorithm === "inversions") return `${fmt(out)} inversões`;
  if (algorithm === "max_subarray") return `soma ${fmt(out.sum)} no trecho [${out.start}, ${out.end})`;
  const shown = out.slice(0, 40).join(", ");
  return out.length > 40 ? `[${shown}, … (${fmt(out.length)} itens)]` : `[${shown}]`;
}

function renderSummary() {
  const m = result.metrics;
  const v = result.verification;
  const node = clear($("lab-summary"));
  node.append(
    el("div", { class: "cards" },
      el("div", { class: "card" }, el("div", { class: "label", text: "Resultado" }), el("div", { class: "value", style: { fontSize: "16px" }, text: outputText() })),
      el("div", { class: "card" }, el("div", { class: "label", text: "Comparações" }), el("div", { class: "value", text: fmt(m.comparisons) }), el("div", { class: "hint", text: m.unit })),
      el("div", { class: "card" }, el("div", { class: "label", text: "Movimentos" }), el("div", { class: "value", text: fmt(m.moves) }), el("div", { class: "hint", text: "escritas/trocas/cópias" })),
      el("div", { class: "card" }, el("div", { class: "label", text: "Chamadas · profundidade" }), el("div", { class: "value", text: `${fmt(m.calls)} · ${m.max_depth}` }), el("div", { class: "hint", text: "profundidade lógica da recursão" })),
      el("div", { class: "card" }, el("div", { class: "label", text: "Tempo" }), el("div", { class: "value", text: fmtMs(m.elapsed_ms) }), el("div", { class: "hint", text: result.trace ? "inclui o registro dos passos" : "sem registro de passos" })),
      el("div", { class: `card${v.ok ? "" : " alerting"}` }, el("div", { class: "label", text: "Verificação" }),
        el("div", { class: "value", style: { fontSize: "16px" } }, el("span", { class: `badge ${v.ok ? "ok" : "bad"}`, text: v.ok ? "✓ confere" : "✗ diverge" })),
        el("div", { class: "hint", text: `contra ${v.source}` }))),
  );
  if (result.kadane) {
    node.append(el("p", { class: "small muted", style: { marginTop: "10px" }, text: `Kadane (programação dinâmica, não D&C): soma ${fmt(result.kadane.sum)} com ${fmt(result.kadane.comparisons)} comparações entre somas, em Θ(n).` }));
  }
  if (!result.trace) {
    node.append(el("p", { class: "banner info", style: { marginTop: "10px" }, text: `Com n = ${fmt(result.input.length)} o passo a passo fica desligado (limite de ${catalog.limits.trace_max_n} elementos); métricas e verificação continuam reais.` }));
  }
  if (result.truncated) {
    node.append(el("p", { class: "banner warn", style: { marginTop: "10px" }, text: "A trilha atingiu o limite de etapas e foi truncada; o resultado e as métricas são da execução completa." }));
  }
}

// ---------------- Desenho do vetor ----------------

function drawBars(values, colorOf, { range = null, mid = null, caption = "" } = {}) {
  const root = clear($("lab-svg"));
  const n = values.length;
  if (!n) {
    root.append(svg("text", { x: W / 2, y: H / 2, "text-anchor": "middle", text: "Vetor vazio" }));
    return;
  }
  const maxAbs = Math.max(1, ...values.map((v) => Math.abs(v)));
  const hasNegative = values.some((v) => v < 0);
  const baseY = hasNegative ? H / 2 : H - PAD - 14;
  const span = hasNegative ? H / 2 - PAD : H - 2 * PAD - 14;
  const bw = (W - 2 * PAD) / n;
  if (range) {
    root.append(svg("rect", { x: PAD + range[0] * bw, y: 4, width: Math.max((range[1] - range[0]) * bw, 2), height: H - 8, fill: "var(--region)", rx: 6 }));
  }
  root.append(svg("line", { x1: PAD, x2: W - PAD, y1: baseY, y2: baseY, stroke: "var(--border)" }));
  values.forEach((value, i) => {
    const h = (Math.abs(value) / maxAbs) * span;
    const y = value >= 0 ? baseY - h : baseY;
    root.append(svg("rect", { x: PAD + i * bw + bw * 0.12, y, width: Math.max(bw * 0.76, 1), height: Math.max(h, 1.5), fill: colorOf(i, value), rx: 2 }));
    if (n <= 32) {
      root.append(svg("text", { x: PAD + i * bw + bw / 2, y: value >= 0 ? y - 4 : y + h + 12, "text-anchor": "middle", text: String(value) }));
    }
  });
  if (mid !== null && mid !== undefined) {
    const x = PAD + mid * bw;
    root.append(svg("line", { x1: x, x2: x, y1: 4, y2: H - 4, stroke: "var(--text)", "stroke-dasharray": "6 5" }));
  }
  if (caption) root.append(svg("text", { x: PAD, y: H - 4, text: caption }));
}

function legend(items) {
  clear($("lab-legend")).append(...items.map(([color, label]) => el("span", {}, el("i", { class: "swatch", style: { background: `var(${color})` } }), label)));
}

function drawStatic() {
  const values = algorithm === "quickselect" || algorithm === "max_subarray" || algorithm === "inversions" ? result.input : result.output;
  drawBars(values.slice(0, 400), () => "var(--accent)", { caption: values.length > 400 ? "primeiros 400 valores" : "" });
  legend([]);
  $("lab-step-title").textContent = "Sem passo a passo";
  $("lab-step-text").textContent = "Reduza n para até 64 para acompanhar as etapas.";
}

function renderStep(index) {
  const step = result.steps[index];
  const inside = (i) => step.lo !== undefined && i >= step.lo && i < step.hi;
  if (algorithm === "merge_sort" || algorithm === "inversions") {
    drawBars(step.array, (i) => {
      if (step.write === i) return "var(--critical)";
      if (step.mid !== undefined && inside(i)) return i < step.mid ? "var(--accent)" : "var(--reference)";
      return inside(i) ? "var(--accent)" : "var(--muted)";
    }, { range: [step.lo, step.hi], mid: step.kind === "base" ? null : step.mid });
    legend([["--accent", "Metade esquerda"], ["--reference", "Metade direita"], ["--critical", "Posição escrita agora"], ["--muted", "Fora do subproblema"]]);
  } else if (algorithm === "quick_sort") {
    drawBars(step.array, (i) => {
      if (i === step.pivot) return "var(--warn)";
      if (step.j === i) return "var(--critical)";
      if (step.i !== undefined && inside(i) && i < step.i) return "var(--ok)";
      return inside(i) ? "var(--accent)" : "var(--muted)";
    }, { range: [step.lo, step.hi] });
    legend([["--warn", "Pivô"], ["--ok", "Já na parte menor"], ["--critical", "Elemento comparado"], ["--accent", "Subproblema"], ["--muted", "Fora do subproblema"]]);
  } else if (algorithm === "quickselect") {
    drawBars(step.array, (i, value) => {
      if (step.answer !== undefined && value === step.answer) return "var(--critical)";
      if (step.pivot === undefined) return "var(--accent)";
      if (value === step.pivot) return "var(--warn)";
      return value < step.pivot ? "var(--accent)" : "var(--reference)";
    }, { caption: `grupo atual: ${step.array.length} elemento(s); procurando o ${step.rank}º menor` });
    legend([["--accent", "Menores que o pivô"], ["--warn", "Iguais ao pivô"], ["--reference", "Maiores"], ["--critical", "Resposta"]]);
  } else {
    const best = step.best;
    const cross = step.cross;
    drawBars(result.input, (i) => {
      if (best && step.kind !== "divide" && i >= best[1] && i < best[2]) return "var(--critical)";
      if (cross && i >= cross[1] && i < cross[2]) return "var(--warn)";
      return inside(i) ? "var(--accent)" : "var(--muted)";
    }, { range: [step.lo, step.hi], mid: step.mid ?? null });
    legend([["--accent", "Subproblema"], ["--warn", "Melhor trecho que cruza o meio"], ["--critical", "Melhor trecho do subproblema"], ["--muted", "Fora"]]);
  }
  const extra = algorithm === "inversions" && step.inversions !== undefined ? ` · inversões contadas: ${fmt(step.inversions)}` : "";
  $("lab-step-title").textContent = `${KIND_LABELS[step.kind] || step.kind} · etapa ${index + 1} de ${result.steps.length}${step.depth !== undefined ? ` · profundidade ${step.depth}` : ""}${extra}`;
  $("lab-step-text").textContent = step.text;
  renderPseudocode($("lab-pseudo"), algorithmById(catalog, algorithm).pseudocode, step.line);
}

// ---------------- Cenário em JSON ----------------

function exportScenario() {
  if (!result) {
    showError($("lab-error"), new ApiError("Execute o algoritmo antes de exportar o cenário."));
    return;
  }
  const { seed, ...parametros } = result.params;
  const scenario = { tipo: SCENARIO_TYPE, versao: 1, modulo: "laboratorio", algoritmo: result.algorithm, seed, parametros, valores: result.input };
  download(`cenario-${result.algorithm}-n${result.input.length}.json`, `${JSON.stringify(scenario, null, 2)}\n`, "application/json");
  announce("Cenário exportado.");
}

/** Valida o cenário importado com os mesmos limites do servidor (que valida de novo ao executar). */
export function parseLabScenario(data, catalogData) {
  if (data.modulo !== "laboratorio") throw new ApiError("Este cenário não é do laboratório.");
  if (!catalogData.lab_algorithms.includes(data.algoritmo)) throw new ApiError("Algoritmo desconhecido no cenário.");
  const values = data.valores;
  if (!Array.isArray(values) || values.length < 1 || values.length > catalogData.limits.lab_max_n
      || !values.every((v) => Number.isInteger(v) && Math.abs(v) <= 1e9)) {
    throw new ApiError(`“valores” deve ter de 1 a ${catalogData.limits.lab_max_n} inteiros (até 10⁹ em módulo).`);
  }
  const seed = data.seed ?? 21;
  if (!Number.isInteger(seed) || seed < 0 || seed > 2147483647) throw new ApiError("“seed” inválida.");
  const params = data.parametros ?? {};
  if (typeof params !== "object" || Array.isArray(params)) throw new ApiError("“parametros” deve ser um objeto.");
  const pivots = catalogData.pivots[data.algoritmo];
  if (params.pivot !== undefined && (!pivots || !pivots.includes(params.pivot))) throw new ApiError("Pivô inválido para este algoritmo.");
  if (params.k !== undefined && (!Number.isInteger(params.k) || params.k < 1 || params.k > values.length)) {
    throw new ApiError(`“k” deve estar entre 1 e ${values.length}.`);
  }
  return { algorithm: data.algoritmo, values, seed, pivot: params.pivot, k: params.k };
}

async function importScenario(file) {
  try {
    const scenario = parseLabScenario(await readJsonFile(file), catalog);
    algorithm = scenario.algorithm;
    $("lab-mode").value = "custom";
    syncControls();
    $("lab-values").value = scenario.values.join(", ");
    $("lab-seed").value = String(scenario.seed);
    if (scenario.pivot) $("lab-pivot").value = scenario.pivot;
    if (scenario.k) $("lab-k").value = String(scenario.k);
    announce("Cenário importado.");
    await run();
  } catch (error) {
    showError($("lab-error"), error);
  }
}

export async function init(params) {
  player = new Player($("lab-player"), $("lab-stage"), renderStep);
  try {
    catalog = await getCatalog();
  } catch (error) {
    showError($("lab-error"), error);
    return;
  }
  $("lab-algorithms").replaceChildren(...catalog.lab_algorithms.map((id) => el("button", {
    type: "button", dataset: { id }, text: algorithmById(catalog, id).name, "aria-pressed": "false",
    onclick: () => {
      algorithm = id;
      syncControls();
      run();
    },
  })));
  $("lab-scenario").replaceChildren(...Object.entries(catalog.array_scenarios).map(([id, text]) => el("option", { value: id, text })));
  if (params.has("alg") && catalog.lab_algorithms.includes(params.get("alg"))) algorithm = params.get("alg");
  $("lab-form").append(scenarioTools({ id: "lab-scenario-json", onExport: exportScenario, onImport: importScenario }));
  $("lab-mode").addEventListener("change", syncControls);
  $("lab-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run();
  });
  syncControls();
  await run();
}

export function onHide() {
  player?.stop();
}

export function onShow(params) {
  if (catalog && params.has("alg") && params.get("alg") !== algorithm && catalog.lab_algorithms.includes(params.get("alg"))) {
    algorithm = params.get("alg");
    syncControls();
    run();
  }
}
