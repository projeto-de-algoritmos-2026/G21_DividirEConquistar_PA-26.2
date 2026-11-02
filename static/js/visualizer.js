// Visualizador do par mais próximo: etapas reais registradas pelo servidor.
import {
  ApiError, Player, SCENARIO_TYPE, announce, api, clear, download, el, fill, readJsonFile, scenarioTools, flightLevel, fmt, isAbort, readInt, renderPseudocode, showError, svg,
} from "./core.js";
import { trafficParams } from "./radar.js";

const $ = (id) => document.getElementById(id);
const W = 800;
const H = 520;
const PAD = 30;
const LABELS = { divide: "Dividir", base: "Caso-base", combine: "Combinar" };

let trace = null;
let player = null;
let scale = null;
let resolvedAt = [];
let rank = [];
let cases = [];
let wantedBand = null;

function setMode(mode) {
  $("viz-mode").value = mode;
  document.querySelectorAll(".viz-case").forEach((node) => { node.hidden = mode !== "case"; });
  document.querySelectorAll(".viz-radar").forEach((node) => { node.hidden = mode !== "radar"; });
  document.querySelectorAll(".viz-custom").forEach((node) => { node.hidden = mode !== "custom"; });
  describeCase();
}

function describeCase() {
  const mode = $("viz-mode").value;
  const node = $("viz-case-description");
  if (mode === "case") {
    const found = cases.find((item) => item.id === $("viz-case").value);
    node.textContent = found ? found.description : "";
  } else if (mode === "radar") {
    node.textContent = "Usa os parâmetros atuais da seção Radar. Coordenadas no plano tangente da faixa, em km; no máximo as 64 primeiras aeronaves da faixa.";
  } else {
    node.textContent = "Coordenadas livres no plano (até 1.000.000 em módulo). Pontos repetidos são permitidos.";
  }
}

function parsePoints(text) {
  const lines = text.split(/\n/).map((line) => line.trim()).filter(Boolean);
  const points = lines.map((line, index) => {
    const parts = line.split(/[\s,;]+/).filter(Boolean).map(Number);
    if (parts.length !== 2 || !parts.every(Number.isFinite)) {
      throw new ApiError(`Linha ${index + 1}: use o formato “x, y” com números.`);
    }
    return parts;
  });
  if (points.length < 2 || points.length > 64) throw new ApiError("Informe de 2 a 64 pontos.");
  return points;
}

async function run() {
  const mode = $("viz-mode").value;
  showError($("viz-error"), null);
  $("viz-points").setAttribute("aria-invalid", "false");
  let request;
  try {
    if (mode === "case") {
      request = api("/api/visualizer", {
        method: "POST", key: "viz",
        body: { case: $("viz-case").value, n: readInt($("viz-n"), "Pontos"), seed: readInt($("viz-seed"), "Seed") },
      });
    } else if (mode === "custom") {
      let points;
      try {
        points = parsePoints($("viz-points").value);
      } catch (error) {
        $("viz-points").setAttribute("aria-invalid", "true");
        throw error;
      }
      request = api("/api/visualizer", { method: "POST", key: "viz", body: { points } });
    } else {
      const params = trafficParams();
      const band = wantedBand ?? $("viz-band").value;
      if (band) params.set("band", band);
      request = api(`/api/steps?${params}`, { key: "viz" });
    }
  } catch (error) {
    showError($("viz-error"), error);
    return;
  }
  $("viz-stage").classList.add("loading");
  try {
    load(await request);
  } catch (error) {
    if (!isAbort(error)) showError($("viz-error"), error);
  } finally {
    $("viz-stage").classList.remove("loading");
  }
}

function load(data) {
  trace = data;
  wantedBand = null;
  if (data.bands) {
    const select = $("viz-band");
    select.replaceChildren(...data.bands.map(([level, count]) =>
      el("option", { value: String(level), text: `${flightLevel(level)} (${count} aeronaves)` })));
    select.value = String(data.flight_level);
  }
  rank = [];
  const rootMembers = data.tree[0]?.members || [];
  rootMembers.forEach((point, position) => { rank[point] = position; });
  resolvedAt = data.tree.map(() => Infinity);
  data.steps.forEach((step, index) => {
    if (step.kind !== "divide") resolvedAt[step.node] = index;
  });
  buildScale(data.points);
  renderResult();
  player.load(data.steps.length);
  announce(`${data.steps.length} etapas carregadas.`);
}

function buildScale(points) {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  // Mesma escala nos dois eixos: a faixa ±δ e as distâncias aparecem sem distorção.
  const k = Math.min((W - 2 * PAD) / (maxX - minX || 1), (H - 2 * PAD) / (maxY - minY || 1));
  const offsetX = (W - (maxX - minX) * k) / 2;
  const offsetY = (H - (maxY - minY) * k) / 2;
  scale = {
    x: (x) => offsetX + (x - minX) * k,
    y: (y) => H - offsetY - (y - minY) * k,
    k,
  };
}

function unit() {
  return trace.labels ? " km" : "";
}

function dist(value) {
  return value === null || value === undefined ? "—" : `${fmt(value, 2)}${unit()}`;
}

function stepText(step) {
  const left = step.left?.distance;
  const right = step.right?.distance;
  if (step.kind === "divide") {
    const leftCount = Math.floor(step.size / 2);
    return `Dividir: ${step.size} pontos ordenados por x. A reta x* = ${fmt(step.middle_x, 2)} separa ${leftCount} à esquerda e ${step.size - leftCount} à direita (posição na ordem por x, que resolve x repetido). Profundidade ${step.depth}.`;
  }
  if (step.kind === "base") {
    const pairs = (step.size * (step.size - 1)) / 2;
    return `Caso-base: ${step.size} ponto(s); compara diretamente todos os ${pairs} par(es). Melhor par deste subproblema: ${dist(step.best?.distance)}.`;
  }
  const improved = step.best && step.delta !== null && step.best.distance < step.delta;
  return `Combinar: δ = min(${dist(left)}, ${dist(right)}) = ${dist(step.delta)}. A faixa |x − x*| < δ tem ${step.strip.length} ponto(s); em ordem de y, cada um é comparado só com os seguintes enquanto Δy < δ — ${step.compared.length} comparação(ões) aqui. `
    + (improved
      ? `A faixa achou um par melhor que cruza a divisão: ${dist(step.best.distance)}.`
      : "Nenhum par da faixa melhora δ: o resultado é o melhor das metades.");
}

function renderStep(index) {
  const step = trace.steps[index];
  const s = scale;
  const root = clear($("viz-svg"));
  const members = new Set(step.members);
  const strip = new Set(step.strip);

  root.append(svg("rect", { x: s.x(step.low_x) - 4, y: 0, width: Math.max(s.x(step.high_x) - s.x(step.low_x) + 8, 8), height: H, fill: "var(--region)" }));
  if (step.kind === "combine" && step.delta !== null) {
    const left = Math.max(0, s.x(step.middle_x - step.delta));
    const right = Math.min(W, s.x(step.middle_x + step.delta));
    root.append(svg("rect", { x: left, y: 0, width: Math.max(right - left, 1), height: H, fill: "var(--strip)" }));
  }
  if (step.middle_x !== null) {
    const x = s.x(step.middle_x);
    root.append(svg("line", { x1: x, x2: x, y1: 0, y2: H, stroke: "var(--text)", "stroke-dasharray": "6 5", "stroke-width": 1.5 }));
    root.append(svg("text", { x: x + 5, y: 16, text: "x*" }));
  }
  for (const [a, b] of step.compared) {
    const [pa, pb] = [trace.points[a], trace.points[b]];
    root.append(svg("line", { x1: s.x(pa[0]), y1: s.y(pa[1]), x2: s.x(pb[0]), y2: s.y(pb[1]), stroke: "var(--reference)", "stroke-width": 1.2, opacity: 0.8 }));
  }
  trace.points.forEach((point, i) => {
    const active = members.has(i);
    root.append(svg("circle", {
      cx: s.x(point[0]), cy: s.y(point[1]), r: strip.has(i) ? 6 : active ? 5 : 3.5,
      fill: strip.has(i) ? "var(--warn)" : active ? "var(--text)" : "var(--muted)",
      opacity: active ? 1 : 0.35, stroke: "var(--surface-2)", "stroke-width": 1.5,
    }));
    if (trace.points.length <= 24) root.append(svg("text", { x: s.x(point[0]) + 7, y: s.y(point[1]) - 7, text: String(i) }));
  });
  if (step.best) {
    const [a, b] = step.best.pair;
    const [pa, pb] = [trace.points[a], trace.points[b]];
    root.append(svg("line", { x1: s.x(pa[0]), y1: s.y(pa[1]), x2: s.x(pb[0]), y2: s.y(pb[1]), stroke: "var(--critical)", "stroke-width": 3.5 }));
    [pa, pb].forEach((p) => root.append(svg("circle", { cx: s.x(p[0]), cy: s.y(p[1]), r: 6.5, fill: "var(--critical)", stroke: "var(--surface-2)", "stroke-width": 2 })));
  }

  $("viz-step-title").textContent = `${LABELS[step.kind]} · etapa ${index + 1} de ${trace.steps.length}${trace.flight_level !== undefined ? ` · ${flightLevel(trace.flight_level)}` : ""}`;
  $("viz-step-text").textContent = stepText(step);
  const kv = clear($("viz-step-kv"));
  const row = (term, value) => kv.append(el("dt", { text: term }), el("dd", { text: value }));
  row("Profundidade", String(step.depth));
  row("Tamanho do subproblema", String(step.size));
  if (step.kind === "combine") row("δ = min(esq., dir.)", dist(step.delta));
  row("Comparações nesta etapa", fmt(step.compared.length));
  row("Comparações acumuladas", fmt(step.comparisons_total));
  row("Melhor par local", step.best ? `${step.best.pair[0]} – ${step.best.pair[1]} · ${dist(step.best.distance)}` : "ainda não definido");
  renderPseudocode($("viz-pseudo"), trace.pseudocode, step.line);
  renderTree(index);
}

function renderTree(index) {
  const step = trace.steps[index];
  const nodes = trace.tree;
  const depth = Math.max(...nodes.map((n) => n.depth));
  const n = trace.points.length;
  const width = 800;
  const rowH = 46;
  const height = (depth + 1) * rowH + 16;
  const xOf = (node) => {
    const ranks = node.members.map((m) => rank[m]);
    return 20 + ((Math.min(...ranks) + Math.max(...ranks)) / 2 / Math.max(n - 1, 1)) * (width - 40);
  };
  const yOf = (node) => 22 + node.depth * rowH;
  const ancestors = new Set();
  for (let id = step.node; id !== null && id !== undefined; id = nodes[id].parent) ancestors.add(id);
  const root = svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": `Árvore de recursão com ${nodes.length} chamadas; profundidade máxima ${depth}` });
  for (const node of nodes) {
    if (node.parent === null) continue;
    const parent = nodes[node.parent];
    root.append(svg("line", { x1: xOf(parent), y1: yOf(parent), x2: xOf(node), y2: yOf(node), stroke: ancestors.has(node.id) ? "var(--accent)" : "var(--border)", "stroke-width": ancestors.has(node.id) ? 2.5 : 1.2 }));
  }
  for (const node of nodes) {
    const current = node.id === step.node;
    const resolved = resolvedAt[node.id] <= index;
    root.append(svg("circle", {
      cx: xOf(node), cy: yOf(node), r: current ? 11 : 8.5,
      fill: current ? "var(--accent)" : resolved ? "var(--surface-3)" : "var(--surface)",
      stroke: current ? "var(--focus)" : resolved ? "var(--ok)" : "var(--border)", "stroke-width": current ? 3 : 1.5,
    }));
    root.append(svg("text", { x: xOf(node), y: yOf(node) + 4, "text-anchor": "middle", style: "font-size:10px", text: String(node.size) }));
  }
  clear($("viz-tree")).append(root);
}

function renderResult() {
  const r = trace.result;
  const v = trace.verification;
  const label = (i) => (trace.labels ? `${trace.labels[i]} (#${i})` : `#${i}`);
  fill($("viz-result"),
    el("h3", { text: "Resultado" }),
    el("dl", { class: "kv" },
      el("dt", { text: "Par mais próximo" }), el("dd", { text: `${label(r.pair[0])} – ${label(r.pair[1])}` }),
      el("dt", { text: "Distância" }), el("dd", { text: dist(r.distance) }),
      el("dt", { text: "Cálculos de distância" }), el("dd", { text: `${fmt(r.comparisons)} (D&C) × ${fmt(v.brute_comparisons)} (força bruta)` }),
      el("dt", { text: "Chamadas / profundidade" }), el("dd", { text: `${fmt(r.calls)} / ${r.max_depth}` }),
      el("dt", { text: "Verificação" }), el("dd", {},
        el("span", { class: `badge ${v.ok ? "ok" : "bad"}`, text: v.ok ? "✓ confere com a força bruta" : "✗ diverge da força bruta" }))),
    trace.labels
      ? el("p", { class: "small muted", text: `${flightLevel(trace.flight_level)}: ${trace.band_size} aeronaves na faixa${trace.sampled ? `, mostradas as 64 primeiras` : ""}. Distância no plano tangente; o radar ainda certifica o par sobre a esfera.` })
      : null,
  );
}

// ---------------- Cenário em JSON ----------------

function exportScenario() {
  if (!trace) {
    showError($("viz-error"), new ApiError("Execute o visualizador antes de exportar o cenário."));
    return;
  }
  const scenario = { tipo: SCENARIO_TYPE, versao: 1, modulo: "visualizador", pontos: trace.points };
  download(`cenario-par-mais-proximo-${trace.points.length}-pontos.json`, `${JSON.stringify(scenario, null, 2)}\n`, "application/json");
  announce("Cenário exportado.");
}

export function parseVisualScenario(data) {
  if (data.modulo !== "visualizador") throw new ApiError("Este cenário não é do visualizador.");
  const points = data.pontos;
  if (!Array.isArray(points) || points.length < 2 || points.length > 64
      || !points.every((p) => Array.isArray(p) && p.length === 2 && p.every((c) => typeof c === "number" && Number.isFinite(c) && Math.abs(c) <= 1e6))) {
    throw new ApiError("“pontos” deve ter de 2 a 64 pares [x, y] finitos, até 1.000.000 em módulo.");
  }
  return points;
}

async function importScenario(file) {
  try {
    const points = parseVisualScenario(await readJsonFile(file));
    setMode("custom");
    $("viz-points").value = points.map(([x, y]) => `${x}, ${y}`).join("\n");
    announce("Cenário importado.");
    await run();
  } catch (error) {
    showError($("viz-error"), error);
  }
}

export async function init(params) {
  player = new Player($("viz-player"), $("viz-stage"), renderStep);
  try {
    const data = await api("/api/visualizer/cases");
    cases = data.cases;
    $("viz-case").replaceChildren(...cases.map((item) => el("option", { value: item.id, text: item.name })));
    $("viz-case").value = "faixa_central";
  } catch (error) {
    showError($("viz-error"), error);
  }
  $("viz-form").append(scenarioTools({ id: "viz-scenario-json", onExport: exportScenario, onImport: importScenario }));
  $("viz-mode").addEventListener("change", () => {
    setMode($("viz-mode").value);
    run();
  });
  $("viz-case").addEventListener("change", () => {
    describeCase();
    run();
  });
  $("viz-band").addEventListener("change", run);
  $("viz-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run();
  });
  setMode(params.has("band") ? "radar" : "case");
  if (!params.has("band")) run();
}

export function onHide() {
  player?.stop();
}

export function onShow(params) {
  if (params.has("band")) {
    wantedBand = params.get("band");
    setMode("radar");
    run();
  }
}
