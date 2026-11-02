// Visão geral: estado do servidor e das fontes, e uma varredura real com os parâmetros padrão do radar.
import { api, el, fill, flightLevel, fmt, fmtMs } from "./core.js";
import { getCatalog } from "./catalog.js";

const $ = (id) => document.getElementById(id);
const DEFAULT_SCAN = new URLSearchParams({ source: "sim", n: "400", seed: "21", minutes: "0", threshold_nm: "5", band_ft: "1000" });
const KPI_LABELS = ["Faixas analisadas", "Abaixo do limiar", "Menor separação", "Cálculos de distância", "Algoritmos D&C"];

function pill(state, ...content) {
  return el("li", { class: `status-pill ${state}` }, el("span", { class: "status-dot", "aria-hidden": "true" }), ...content);
}

function card(label, value, hint, alerting = false) {
  return el("div", { class: `card${alerting ? " alerting" : ""}` },
    el("div", { class: "label", text: label }),
    el("div", { class: "value", text: value }),
    hint ? el("div", { class: "hint" }, hint) : null);
}

async function loadStatus() {
  const list = $("overview-status");
  try {
    const health = await api("/api/health");
    const snapshot = health.snapshot;
    let snapshotPill;
    if (snapshot.available) {
      const when = snapshot.captured_at_local
        ? new Date(snapshot.captured_at_local).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo", dateStyle: "short", timeStyle: "short" })
        : "data não informada";
      snapshotPill = pill("ok", el("span", {}, el("strong", { text: "Snapshot histórico" }), ` · ${fmt(snapshot.records)} registros · capturado em ${when}`));
    } else {
      snapshotPill = pill("warn", el("span", {}, el("strong", { text: "Snapshot histórico" }), " indisponível; a simulação continua funcionando"));
    }
    fill(list,
      pill("ok", el("span", {}, el("strong", { text: "Servidor" }), " ativo")),
      pill("ok", el("span", {}, el("strong", { text: "Simulação" }), " determinística por seed")),
      snapshotPill);
  } catch (error) {
    fill(list, pill("bad", el("span", {}, el("strong", { text: "Servidor" }), ` indisponível: ${error.message}`)));
  }
}

async function loadKpis() {
  const grid = $("overview-kpis");
  fill(grid, ...KPI_LABELS.map((label) => card(label, "…", "carregando")));
  grid.classList.add("loading");
  try {
    const [scan, catalog] = await Promise.all([api(`/api/scan?${DEFAULT_SCAN}`), getCatalog()]);
    const s = scan.summary;
    const work = s.comparisons + s.candidate_pairs;
    // Força bruta compararia todos os pares de cada faixa: Σ c(c − 1)/2.
    const brute = scan.bands.reduce((total, band) => total + (band.aircraft_count * (band.aircraft_count - 1)) / 2, 0);
    fill(grid,
      card("Faixas analisadas", fmt(s.bands_analyzed), `de ${fmt(s.bands_total)} faixas · ${fmt(s.aircraft)} aeronaves`),
      card("Abaixo do limiar", fmt(s.bands_below_threshold), `par mínimo < ${fmt(s.separation_nm, 1)} NM`, s.bands_below_threshold > 0),
      card("Menor separação", s.min_distance_nm === null ? "—" : `${fmt(s.min_distance_nm, 2)} NM`,
        s.min_distance_nm === null ? "nenhuma faixa com 2 aeronaves" : `${fmt(s.min_distance_nm * 1.852, 2)} km · ${flightLevel(s.min_flight_level)}`),
      card("Cálculos de distância", fmt(work), brute > 0 ? `força bruta: ${fmt(brute)} (${fmt(brute / Math.max(work, 1), 0)}× mais)` : "sem pares para comparar"),
      card("Algoritmos D&C", fmt(catalog.algorithms.length), "radar + laboratório, com referência"));
    $("overview-kpi-caption").textContent = `Simulação seed ${scan.source.seed} · ${fmt(scan.source.records)} aeronaves · minuto ${scan.source.minutes} · calculada agora em ${fmtMs(s.elapsed_ms)}.`;
  } catch (error) {
    fill(grid, el("p", { class: "banner error", role: "alert", style: { gridColumn: "1 / -1", margin: 0 }, text: `Não foi possível calcular a execução de referência: ${error.message}` }));
  } finally {
    grid.classList.remove("loading");
  }
}

export function init() {
  return Promise.all([loadStatus(), loadKpis()]);
}
