// Benchmark: tamanhos configuráveis, repetições, mediana/dispersão, gráficos e exportação.
import { ApiError, api, clear, download, el, fmt, fmtMs, isAbort, readInt, setBusy, showError, sortableTable } from "./core.js";
import { algorithmById, getCatalog } from "./catalog.js";
import { logLogChart } from "./chart.js";
import { PIVOT_LABELS } from "./lab.js";

const $ = (id) => document.getElementById(id);
let catalog = null;
let report = null;

function syncControls() {
  const id = $("bench-algorithm").value;
  const scenarios = id === "closest_pair" ? catalog.point_scenarios : catalog.array_scenarios;
  const previous = $("bench-scenario").value;
  $("bench-scenario").replaceChildren(...Object.entries(scenarios).map(([key, text]) => el("option", { value: key, text })));
  $("bench-scenario").value = scenarios[previous] ? previous : "aleatorio";
  const pivots = catalog.pivots[id];
  document.querySelector(".bench-pivot").hidden = !pivots;
  if (pivots) {
    $("bench-pivot").replaceChildren(...pivots.map((p) => el("option", { value: p, text: PIVOT_LABELS[p] })));
    $("bench-pivot").value = id === "quick_sort" ? "ultimo" : "aleatorio";
  }
  const l = catalog.limits;
  $("bench-limits").textContent = `Limites: até ${l.bench_max_sizes} tamanhos e ${l.bench_max_repeats} repetições; n até ${fmt(l.bench_max_n)} (3.000 quando o próprio algoritmo pode degradar para Θ(n²), como Quick Sort com pivô fixo ou muitos iguais); referência Θ(n²) só até n = ${fmt(l.reference_max_n)}; orçamento total de 20 s — tamanhos além dele aparecem como não executados.`;
}

function readSizes() {
  const parts = $("bench-sizes").value.split(/[\s,;]+/).filter(Boolean);
  const sizes = parts.map(Number);
  const ok = sizes.length >= 1 && sizes.length <= catalog.limits.bench_max_sizes && sizes.every((n) => Number.isInteger(n) && n >= 1);
  $("bench-sizes").setAttribute("aria-invalid", ok ? "false" : "true");
  if (!ok) throw new ApiError(`Tamanhos: de 1 a ${catalog.limits.bench_max_sizes} inteiros positivos separados por vírgula.`);
  return sizes;
}

async function run() {
  const form = $("bench-form");
  showError($("bench-error"), null);
  let params;
  try {
    params = new URLSearchParams({
      algorithm: $("bench-algorithm").value,
      scenario: $("bench-scenario").value,
      sizes: readSizes().join(","),
      repeats: readInt($("bench-repeats"), "Repetições"),
      seed: readInt($("bench-seed"), "Seed"),
      warmup: $("bench-warmup").checked ? "1" : "0",
    });
    if (catalog.pivots[params.get("algorithm")]) params.set("pivot", $("bench-pivot").value);
  } catch (error) {
    showError($("bench-error"), error);
    return;
  }
  setBusy(form, true, "Medindo… (até 20 s)");
  $("bench-result").classList.add("loading");
  try {
    report = await api(`/api/benchmark?${params}`, { key: "bench" });
    render();
  } catch (error) {
    if (!isAbort(error)) showError($("bench-error"), error);
  } finally {
    setBusy(form, false);
    $("bench-result").classList.remove("loading");
  }
}

function refName() {
  return report.rows.find((row) => row.reference)?.reference.name || "Referência";
}

function render() {
  const info = algorithmById(catalog, report.algorithm);
  const rows = report.rows;
  const dcLabel = `${info.name} (D&C)`;
  const series = (key, pick) => [
    { label: dcLabel, className: "series-dc", points: rows.filter((r) => r.dc).map((r) => pick(r.dc, r)) },
    { label: refName(), className: "series-ref", points: rows.filter((r) => r.reference).map((r) => pick(r.reference, r)) },
  ];
  const env = report.environment;
  const table = sortableTable({
    caption: `Unidade de operações: ${report.unit}`,
    columns: [
      { key: "n", label: "n", num: true, value: (r) => r.n, render: (r) => fmt(r.n) },
      { key: "dc", label: "D&C mediana", num: true, value: (r) => r.dc?.median_ms ?? null, render: (r) => (r.dc ? fmtMs(r.dc.median_ms) : "não executado") },
      { key: "dcspread", label: "mín – máx (desvio)", value: (r) => r.dc?.stdev_ms ?? null, render: (r) => (r.dc ? `${fmtMs(r.dc.min_ms)} – ${fmtMs(r.dc.max_ms)} (${fmtMs(r.dc.stdev_ms)})` : "—") },
      { key: "ref", label: "Ref. mediana", num: true, value: (r) => r.reference?.median_ms ?? null, render: (r) => (r.reference ? fmtMs(r.reference.median_ms) : "não executada") },
      { key: "dcops", label: "Operações D&C", num: true, value: (r) => r.dc?.comparisons ?? null, render: (r) => (r.dc ? fmt(r.dc.comparisons) : "—") },
      { key: "refops", label: "Operações ref.", num: true, value: (r) => r.reference?.comparisons ?? null, render: (r) => (r.reference ? fmt(r.reference.comparisons) : "—") },
      { key: "ok", label: "Confere", value: (r) => r.dc?.verified ?? null, render: (r) => {
        if (!r.dc) return "—";
        if (r.dc.verified === null) return el("span", { class: "badge neutral", title: "sem referência neste n", text: "n/d" });
        return el("span", { class: `badge ${r.dc.verified ? "ok" : "bad"}`, text: r.dc.verified ? "✓" : "✗" });
      } },
      { key: "note", label: "Observação", value: (r) => r.skipped || r.reference_skipped || "", render: (r) => r.skipped || r.reference_skipped || "" },
    ],
  });
  table.update(rows);
  clear($("bench-result")).append(
    el("div", { class: "grid-2" },
      logLogChart({
        title: "Tempo mediano", yLabel: "ms (mediana; barra = mín–máx)", format: (v) => fmtMs(v),
        series: series("ms", (m, r) => ({ x: r.n, y: m.median_ms, low: m.min_ms, high: m.max_ms })),
      }),
      logLogChart({
        title: "Operações", yLabel: report.unit, format: (v) => fmt(v),
        series: series("ops", (m, r) => ({ x: r.n, y: m.comparisons })),
      })),
    el("div", { class: "table-wrap", style: { marginTop: "12px" } }, table.element),
    el("p", { class: "small muted", style: { marginTop: "8px" }, text: `Cenário: ${report.scenario} · seed ${report.seed} · ${report.repeats} repetição(ões)${report.warmup ? " + aquecimento" : ""}${report.params.pivot ? ` · pivô ${PIVOT_LABELS[report.params.pivot]}` : ""}. Ambiente: ${env.implementation} ${env.python}, ${env.platform}, ${env.cpus} CPU(s), ${env.date}.` }),
    el("div", { class: "segmented", style: { marginTop: "8px" } },
      el("button", { type: "button", text: "⬇ Exportar CSV", onclick: exportCsv }),
      el("button", { type: "button", text: "⬇ Exportar JSON", onclick: () => download(`benchmark-${report.algorithm}.json`, JSON.stringify(report, null, 2), "application/json") })),
  );
}

function exportCsv() {
  const header = ["algorithm", "scenario", "seed", "n", "dc_median_ms", "dc_min_ms", "dc_max_ms", "dc_stdev_ms", "dc_operations",
    "dc_verified", "reference", "ref_median_ms", "ref_min_ms", "ref_max_ms", "ref_stdev_ms", "ref_operations", "note"];
  const cell = (value) => {
    const text = value === null || value === undefined ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const lines = [header.join(",")];
  for (const r of report.rows) {
    lines.push([report.algorithm, report.scenario, report.seed, r.n,
      r.dc?.median_ms, r.dc?.min_ms, r.dc?.max_ms, r.dc?.stdev_ms, r.dc?.comparisons, r.dc?.verified,
      r.reference?.name, r.reference?.median_ms, r.reference?.min_ms, r.reference?.max_ms, r.reference?.stdev_ms,
      r.reference?.comparisons, r.skipped || r.reference_skipped].map(cell).join(","));
  }
  download(`benchmark-${report.algorithm}.csv`, `${lines.join("\n")}\n`, "text/csv");
}

export async function init() {
  try {
    catalog = await getCatalog();
  } catch (error) {
    showError($("bench-error"), error);
    return;
  }
  $("bench-algorithm").replaceChildren(...catalog.algorithms.map((a) => el("option", { value: a.id, text: a.name })));
  $("bench-algorithm").addEventListener("change", syncControls);
  $("bench-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run();
  });
  syncControls();
}
