// Comparação lado a lado: os seis algoritmos D&C contra referências, mesma entrada.
import { api, clear, el, fmt, fmtMs, isAbort, readInt, setBusy, showError, sortableTable } from "./core.js";
import { getCatalog } from "./catalog.js";

const $ = (id) => document.getElementById(id);
let table = null;

async function run() {
  const form = $("compare-form");
  showError($("compare-error"), null);
  let params;
  try {
    params = new URLSearchParams({
      scenario: $("compare-scenario").value,
      n: readInt($("compare-n"), "n"),
      seed: readInt($("compare-seed"), "Seed"),
      repeats: readInt($("compare-repeats"), "Repetições"),
    });
  } catch (error) {
    showError($("compare-error"), error);
    return;
  }
  setBusy(form, true, "Medindo…");
  $("compare-result").classList.add("loading");
  try {
    const data = await api(`/api/compare?${params}`, { key: "compare" });
    render(data);
  } catch (error) {
    if (!isAbort(error)) showError($("compare-error"), error);
  } finally {
    setBusy(form, false);
    $("compare-result").classList.remove("loading");
  }
}

function render(data) {
  const node = clear($("compare-result"));
  node.append(
    el("p", { class: "small muted", text: `n = ${fmt(data.n)} · seed ${data.seed} · mediana de ${data.repeats} repetição(ões) · Python ${data.environment.python} · ${data.environment.date}` }),
    el("div", { class: "table-wrap" }, table.element),
    el("p", { class: "small muted", style: { marginTop: "8px" }, text: "“Razão” = operações da referência ÷ operações do D&C, na unidade da linha. Quick Sort e Quickselect usam o pivô padrão (último e aleatório). O par mais próximo usa pontos gerados pela mesma seed; quando o cenário de vetor não existe para pontos, usa pontos uniformes." }),
  );
  table.update(data.rows);
}

export async function init() {
  const catalog = await getCatalog().catch((error) => {
    showError($("compare-error"), error);
    return null;
  });
  if (!catalog) return;
  $("compare-scenario").replaceChildren(...Object.entries(catalog.array_scenarios).map(([id, text]) => el("option", { value: id, text })));
  table = sortableTable({
    caption: "Tempo e operações sobre a mesma entrada",
    columns: [
      { key: "name", label: "Algoritmo", value: (r) => r.name, render: (r) => el("span", {}, el("strong", { text: r.name }), el("br"), el("span", { class: "small muted", text: r.input })) },
      { key: "dc_ms", label: "D&C", num: true, value: (r) => r.dc_ms, render: (r) => fmtMs(r.dc_ms) },
      { key: "ref", label: "Referência", value: (r) => r.reference_name, render: (r) => r.reference_name },
      { key: "ref_ms", label: "Tempo ref.", num: true, value: (r) => r.reference_ms, render: (r) => fmtMs(r.reference_ms) },
      { key: "dc_ops", label: "Operações D&C", num: true, value: (r) => r.dc_comparisons, render: (r) => fmt(r.dc_comparisons) },
      { key: "ref_ops", label: "Operações ref.", num: true, value: (r) => r.reference_comparisons, render: (r) => fmt(r.reference_comparisons) },
      { key: "ratio", label: "Razão", num: true, value: (r) => r.reference_comparisons / r.dc_comparisons, render: (r) => `${fmt(r.reference_comparisons / r.dc_comparisons, 1)}×` },
      { key: "unit", label: "Unidade", value: (r) => r.unit, render: (r) => r.unit },
      { key: "ok", label: "Verificado", value: (r) => (r.verified ? 1 : 0), render: (r) => el("span", { class: `badge ${r.verified ? "ok" : "bad"}`, title: r.verified_by, text: r.verified ? "✓" : "✗" }) },
    ],
  });
  $("compare-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run();
  });
}
