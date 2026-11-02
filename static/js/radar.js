// Radar: parâmetros, mapa Leaflet, cartões de resumo, filtros e tabela de faixas.
import {
  announce, api, el, fill, flightLevel, fmt, fmtMs, isAbort, readFloat, readInt, showError, sortableTable,
} from "./core.js";

const $ = (id) => document.getElementById(id);
const form = () => $("radar-form");
const inputs = {
  get source() { return $("radar-source"); },
  get n() { return $("radar-n"); },
  get seed() { return $("radar-seed"); },
  get minutes() { return $("radar-minutes"); },
  get threshold() { return $("radar-threshold"); },
  get band() { return $("radar-band"); },
  get allPairs() { return $("radar-allpairs"); },
};

const PRESETS = {
  padrao: { source: "sim", n: 400, seed: 21, minutes: 0, threshold_nm: 5, band_ft: 1000, all_pairs: false },
  leve: { source: "sim", n: 100, seed: 7, minutes: 0, threshold_nm: 5, band_ft: 1000, all_pairs: false },
  denso: { source: "sim", n: 2000, seed: 21, minutes: 0, threshold_nm: 5, band_ft: 1000, all_pairs: true },
  estrito: { source: "sim", n: 400, seed: 21, minutes: 0, threshold_nm: 3, band_ft: 1000, all_pairs: false },
  faixas500: { source: "sim", n: 400, seed: 21, minutes: 0, threshold_nm: 5, band_ft: 500, all_pairs: false },
  snapshot: { source: "opensky", threshold_nm: 5, band_ft: 1000, all_pairs: false },
};

let data = null;
let selectedLevel = null;
let map = null;
let layers = null;
let table = null;
let playTimer = null;
let playing = false;
const DEFAULT_VIEW = { center: [-15, -50], zoom: 4 };

/** Parâmetros de tráfego validados (também usados pelo visualizador). */
export function trafficParams() {
  const params = new URLSearchParams({ source: inputs.source.value, band_ft: inputs.band.value });
  if (inputs.source.value === "sim") {
    params.set("n", readInt(inputs.n, "Aeronaves"));
    params.set("seed", readInt(inputs.seed, "Seed"));
    params.set("minutes", readInt(inputs.minutes, "Minuto"));
  }
  return params;
}

function scanParams() {
  const params = trafficParams();
  params.set("threshold_nm", readFloat(inputs.threshold, "Limiar"));
  if (inputs.allPairs.checked) params.set("all_pairs", "1");
  return params;
}

function applyValues(values) {
  if (values.source) inputs.source.value = values.source;
  if (values.n !== undefined) inputs.n.value = values.n;
  if (values.seed !== undefined) inputs.seed.value = values.seed;
  if (values.minutes !== undefined) inputs.minutes.value = values.minutes;
  if (values.threshold_nm !== undefined) inputs.threshold.value = values.threshold_nm;
  if (values.band_ft !== undefined) inputs.band.value = String(values.band_ft);
  if (values.all_pairs !== undefined) inputs.allPairs.checked = Boolean(values.all_pairs);
  syncSourceControls();
}

function syncSourceControls() {
  const simulated = inputs.source.value === "sim";
  form().querySelectorAll(".sim-only").forEach((node) => { node.hidden = !simulated; });
  if (!simulated) stopPlaying();
  $("radar-minutes-out").textContent = inputs.minutes.value;
}

// ---------------- Requisição ----------------

async function refresh() {
  let params;
  try {
    params = scanParams();
  } catch (error) {
    showError($("radar-error"), error);
    stopPlaying();
    return false;
  }
  $("radar-cards").classList.add("loading");
  form().setAttribute("aria-busy", "true");
  try {
    const result = await api(`/api/scan?${params}`, { key: "scan" });
    data = result;
    showError($("radar-error"), null);
    // Uma resposta que chega depois de o usuário sair do radar não pode reescrever a URL de outra seção.
    if (window.location.hash.startsWith("#radar")) window.history.replaceState(null, "", `#radar?${params}`);
    if (selectedLevel !== null && !data.bands.some((band) => band.flight_level === selectedLevel)) selectedLevel = null;
    render();
    return true;
  } catch (error) {
    if (isAbort(error)) return false;
    showError($("radar-error"), error);
    stopPlaying();
    return false;
  } finally {
    $("radar-cards").classList.remove("loading");
    form().setAttribute("aria-busy", "false");
  }
}

// ---------------- Renderização ----------------

function render() {
  renderSource();
  renderFilterOptions();
  renderCards();
  renderView();
}

function renderView() {
  const visible = filteredAircraft();
  drawMap(visible);
  table.update(filteredBands());
  table.select(selectedLevel);
  renderDetail();
}

function renderSource() {
  const source = data.source;
  const banner = $("radar-source-banner");
  if (source.kind === "sim") {
    banner.className = "banner info";
    banner.replaceChildren(el("span", {},
      el("strong", { text: "Simulação determinística" }),
      ` · seed ${source.seed} · minuto ${source.minutes} · ${fmt(source.records)} aeronaves. `,
      "Voos em linha reta entre aeroportos; as proximidades são produto do modelo, não de tráfego real."));
    return;
  }
  const when = source.captured_at_local
    ? new Date(source.captured_at_local).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" })
    : "data não informada";
  banner.className = "banner info";
  banner.replaceChildren(el("span", {},
    el("strong", { text: "Snapshot histórico da OpenSky Network" }),
    ` · capturado em ${when} (horário de Brasília) · ${fmt(source.records)} registros, ${fmt(source.discarded)} descartados · captura única, sem atualização.`));
}

function airlineOf(plane) {
  const prefix = String(plane.callsign || "").slice(0, 3).toUpperCase();
  return /^[A-Z]{3}$/.test(prefix) ? prefix : "outros";
}

function renderFilterOptions() {
  const airlineSelect = $("filter-airline");
  const levelSelect = $("filter-level");
  const airlines = [...new Set(data.aircraft.map(airlineOf))].sort();
  const levels = data.bands.map((band) => band.flight_level);
  const keep = (select, values) => {
    const value = select.value;
    const first = select.options[0];
    select.replaceChildren(first, ...values.map(([key, label]) => el("option", { value: key, text: label })));
    select.value = values.some(([key]) => key === value) ? value : "";
  };
  keep(airlineSelect, airlines.map((code) => [code, code]));
  keep(levelSelect, levels.map((level) => [String(level), flightLevel(level)]));
}

function filters() {
  return {
    search: $("filter-search").value.trim().toUpperCase(),
    airline: $("filter-airline").value,
    level: $("filter-level").value === "" ? null : Number($("filter-level").value),
    alertOnly: $("filter-alert").checked,
  };
}

function alertLevels() {
  return new Set(data.bands.filter((band) => band.alert).map((band) => band.flight_level));
}

function planeMatches(plane, f, alerts) {
  if (f.search && !String(plane.callsign).toUpperCase().includes(f.search)) return false;
  if (f.airline && airlineOf(plane) !== f.airline) return false;
  if (f.level !== null && plane.flight_level !== f.level) return false;
  if (f.alertOnly && !alerts.has(plane.flight_level)) return false;
  return true;
}

function filteredAircraft() {
  const f = filters();
  const alerts = alertLevels();
  return new Set(data.aircraft.filter((plane) => planeMatches(plane, f, alerts)).map((plane) => plane.id));
}

function filteredBands() {
  const f = filters();
  const alerts = alertLevels();
  const levelsWithMatch = new Set(data.aircraft.filter((plane) => planeMatches(plane, f, alerts)).map((p) => p.flight_level));
  return data.bands.filter((band) => levelsWithMatch.has(band.flight_level));
}

function card(label, value, hint, alerting = false) {
  return el("div", { class: `card${alerting ? " alerting" : ""}` },
    el("div", { class: "label", text: label }),
    el("div", { class: "value", text: value }),
    hint ? el("div", { class: "hint", text: hint }) : null);
}

function renderCards() {
  const s = data.summary;
  const visible = filteredAircraft().size;
  const cards = [
    card("Aeronaves", fmt(s.aircraft), visible === s.aircraft ? "todas visíveis" : `${fmt(visible)} visíveis com os filtros`),
    card("Faixas analisadas", fmt(s.bands_analyzed), `de ${fmt(s.bands_total)} faixas; ${fmt(s.bands_single)} com 1 aeronave`),
    card("Faixas abaixo do limiar", fmt(s.bands_below_threshold),
      `par mínimo < ${fmt(s.separation_nm, 1)} NM (parâmetro do modelo)`, s.bands_below_threshold > 0),
    card("Menor separação", s.min_distance_nm === null ? "—" : `${fmt(s.min_distance_nm, 2)} NM`,
      s.min_distance_nm === null ? "nenhuma faixa com 2 aeronaves" : `${fmt(s.min_distance_nm * 1.852, 2)} km · ${flightLevel(s.min_flight_level)}`),
    card("Tempo de análise", fmtMs(s.elapsed_ms), "medido no servidor, todas as faixas"),
    card("Cálculos de distância", fmt(s.comparisons),
      `D&C no plano + ${fmt(s.candidate_pairs)} candidato(s) na certificação`),
  ];
  if (s.close_pairs !== undefined) {
    cards.push(card("Pares abaixo do limiar", fmt(s.close_pairs),
      s.close_pairs_truncated ? "lista truncada em 500 por faixa" : "todos os pares, por busca em grade"));
  }
  if (s.projection_corrections) {
    cards.push(card("Correções da certificação", fmt(s.projection_corrections), "faixas em que o par do plano não era o geodésico"));
  }
  $("radar-cards").replaceChildren(...cards);
}

function renderDetail() {
  const node = $("band-detail");
  const band = data.bands.find((item) => item.flight_level === selectedLevel);
  if (!band) {
    node.hidden = true;
    return;
  }
  const [a, b] = band.pair;
  const describe = (plane) => `${plane.callsign} · ${fmt(plane.altitude_ft)} ft${plane.route ? ` · ${plane.route}` : ""}`;
  node.hidden = false;
  fill(node,
    el("strong", { text: `${flightLevel(band.flight_level)} · ${fmt(band.aircraft_count)} aeronaves` }),
    el("span", { text: `Par mínimo: ${describe(a)}  ↔  ${describe(b)}` }),
    el("span", { text: `Distância de círculo máximo: ${fmt(band.distance_nm, 2)} NM (${fmt(band.distance_km, 2)} km) — ${band.alert ? "abaixo" : "acima"} do limiar de ${fmt(data.summary.separation_nm, 1)} NM.` }),
    el("span", { class: "muted", text: `${fmt(band.comparisons)} cálculos de distância no D&C; ${fmt(band.candidate_pairs)} candidato(s) conferido(s) na esfera${band.projection_corrected ? " — a certificação trocou o par do plano" : ""}.` }),
    band.close_pairs ? el("span", { text: `${fmt(band.close_pairs.length)} par(es) abaixo do limiar nesta faixa${band.close_pairs_truncated ? " (lista truncada)" : ""}.` }) : null,
    el("div", { class: "segmented" },
      el("button", { type: "button", text: "Aproximar no mapa", onclick: () => zoomToBand(band) }),
      el("button", { type: "button", text: "Ver passo a passo desta faixa", onclick: () => { window.location.hash = `visualizador?band=${band.flight_level}`; } })),
  );
}

// ---------------- Mapa ----------------

function initMap() {
  if (!window.L) {
    $("map").replaceChildren(el("p", { class: "empty", text: "O mapa (Leaflet) não carregou — verifique a conexão com a internet. Cartões, filtros e tabela continuam funcionando." }));
    $("map-reset").disabled = true;
    return;
  }
  map = window.L.map("map", { preferCanvas: true, worldCopyJump: true, zoomControl: true })
    .setView(DEFAULT_VIEW.center, DEFAULT_VIEW.zoom);
  window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 12, attribution: "&copy; colaboradores do OpenStreetMap",
  }).addTo(map);
  layers = {
    planes: window.L.layerGroup().addTo(map),
    pairs: window.L.layerGroup().addTo(map),
    selection: window.L.layerGroup().addTo(map),
  };
  $("map-reset").addEventListener("click", () => map.setView(DEFAULT_VIEW.center, DEFAULT_VIEW.zoom));
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function drawMap(visible) {
  if (!map) return;
  const colors = { normal: cssVar("--accent"), alert: cssVar("--critical"), selected: cssVar("--warn"), dim: cssVar("--muted") };
  const alertIds = new Set();
  data.bands.filter((band) => band.alert).forEach((band) => band.pair.forEach((plane) => alertIds.add(plane.id)));
  layers.planes.clearLayers();
  layers.pairs.clearLayers();
  layers.selection.clearLayers();

  for (const plane of data.aircraft) {
    const shown = visible.has(plane.id);
    const marker = window.L.circleMarker([plane.lat, plane.lon], {
      radius: shown ? (alertIds.has(plane.id) ? 5 : 3.5) : 2,
      color: shown ? (alertIds.has(plane.id) ? colors.alert : colors.normal) : colors.dim,
      weight: 1,
      fillOpacity: shown ? 0.85 : 0.25,
      opacity: shown ? 1 : 0.35,
    });
    marker.bindTooltip(el("span", { text: `${plane.callsign} · ${flightLevel(plane.flight_level)} · ${fmt(plane.altitude_ft)} ft` }));
    marker.on("click", () => selectBand(plane.flight_level, false));
    marker.addTo(layers.planes);
  }

  const byId = new Map(data.aircraft.map((plane) => [plane.id, plane]));
  for (const band of data.bands) {
    if (band.close_pairs) {
      for (const pair of band.close_pairs) {
        const [a, b] = pair.ids.map((id) => byId.get(id));
        if (!a || !b || !(visible.has(a.id) || visible.has(b.id))) continue;
        window.L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: colors.selected, weight: 2, dashArray: "5 5" })
          .bindTooltip(el("span", { text: `${a.callsign} ↔ ${b.callsign} · ${fmt(pair.distance_nm, 2)} NM` }))
          .addTo(layers.pairs);
      }
    }
    if (!band.alert) continue;
    const [a, b] = band.pair;
    if (!visible.has(a.id) && !visible.has(b.id)) continue;
    window.L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: colors.alert, weight: 3 }).addTo(layers.pairs);
    window.L.marker([a.lat, a.lon], {
      keyboard: false,
      icon: window.L.divIcon({
        className: "",
        html: el("span", { class: "conflict-label", text: `${flightLevel(band.flight_level)} · ${fmt(band.distance_nm, 1)} NM` }),
        iconAnchor: [-10, 10],
      }),
    }).addTo(layers.pairs);
  }

  const band = data.bands.find((item) => item.flight_level === selectedLevel);
  if (band) {
    const [a, b] = band.pair;
    window.L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: colors.selected, weight: 4 }).addTo(layers.selection);
    [a, b].forEach((plane) => {
      window.L.circleMarker([plane.lat, plane.lon], { radius: 9, color: colors.selected, weight: 3, fillOpacity: 0 })
        .addTo(layers.selection);
    });
  }
}

function zoomToBand(band) {
  if (!map) return;
  const [a, b] = band.pair;
  map.fitBounds([[a.lat, a.lon], [b.lat, b.lon]], { maxZoom: 9, padding: [80, 80] });
}

function selectBand(level, zoom = true) {
  selectedLevel = level;
  const band = data.bands.find((item) => item.flight_level === level);
  renderView();
  if (band) {
    if (zoom) zoomToBand(band);
    announce(`${flightLevel(level)} selecionada: ${fmt(band.distance_nm, 2)} NM`);
  }
}

// ---------------- Reprodução ----------------

function stopPlaying() {
  playing = false;
  window.clearTimeout(playTimer);
  playTimer = null;
  const button = $("radar-play");
  if (button) {
    button.textContent = "▶ Reproduzir";
    button.setAttribute("aria-pressed", "false");
  }
}

function startPlaying() {
  playing = true;
  $("radar-play").textContent = "⏸ Pausar";
  $("radar-play").setAttribute("aria-pressed", "true");
  const tick = async () => {
    if (!playing) return;
    const max = Number(inputs.minutes.max);
    inputs.minutes.value = (Number(inputs.minutes.value) + 1) % (max + 1);
    $("radar-minutes-out").textContent = inputs.minutes.value;
    const ok = await refresh();
    // Só agenda o próximo quadro depois da resposta: as requisições nunca se acumulam.
    if (playing && ok) playTimer = window.setTimeout(tick, Number($("radar-speed").value));
  };
  playTimer = window.setTimeout(tick, 0);
}

// ---------------- Inicialização ----------------

function readUrl(params) {
  const values = {};
  for (const key of ["source", "n", "seed", "minutes", "threshold_nm", "band_ft"]) {
    if (params.has(key)) values[key] = params.get(key);
  }
  if (params.has("all_pairs")) values.all_pairs = params.get("all_pairs") === "1";
  return values;
}

export function init(params) {
  applyValues(readUrl(params));
  initMap();
  table = sortableTable({
    caption: "Par mínimo por faixa. Clique numa linha para destacar.",
    rowKey: (band) => band.flight_level,
    onRowClick: (band) => selectBand(band.flight_level),
    rowClass: (band) => (band.alert ? "alert" : ""),
    sort: { key: "distance", dir: 1 },
    empty: "Nenhuma faixa corresponde aos filtros.",
    columns: [
      { key: "level", label: "Faixa", value: (b) => b.flight_level, render: (b) => `${b.alert ? "⚠ " : ""}${flightLevel(b.flight_level)}` },
      { key: "count", label: "Aeronaves", num: true, value: (b) => b.aircraft_count, render: (b) => fmt(b.aircraft_count) },
      { key: "pair", label: "Par mínimo", value: (b) => b.pair[0].callsign, render: (b) => `${b.pair[0].callsign} / ${b.pair[1].callsign}` },
      { key: "distance", label: "NM", num: true, value: (b) => b.distance_nm, render: (b) => fmt(b.distance_nm, 2) },
      { key: "km", label: "km", num: true, value: (b) => b.distance_km, render: (b) => fmt(b.distance_km, 1) },
    ],
  });
  $("bands-table").append(table.element);

  const debounced = (() => {
    let timer = null;
    return () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(refresh, 250);
    };
  })();
  [inputs.source, inputs.band, inputs.allPairs].forEach((input) => input.addEventListener("change", () => {
    $("radar-preset").value = "";
    syncSourceControls();
    refresh();
  }));
  [inputs.n, inputs.seed, inputs.threshold].forEach((input) => input.addEventListener("input", () => {
    $("radar-preset").value = "";
    debounced();
  }));
  inputs.minutes.addEventListener("input", () => {
    $("radar-minutes-out").textContent = inputs.minutes.value;
    debounced();
  });
  form().addEventListener("submit", (event) => {
    event.preventDefault();
    refresh();
  });
  $("radar-preset").addEventListener("change", (event) => {
    const preset = PRESETS[event.target.value];
    if (!preset) return;
    stopPlaying();
    applyValues(preset);
    refresh();
  });
  $("radar-play").addEventListener("click", () => (playing ? stopPlaying() : startPlaying()));
  $("radar-restart").addEventListener("click", () => {
    stopPlaying();
    inputs.minutes.value = 0;
    $("radar-minutes-out").textContent = "0";
    refresh();
  });
  $("radar-share").addEventListener("click", async () => {
    let params;
    try {
      params = scanParams();
    } catch (error) {
      showError($("radar-error"), error);
      return;
    }
    const link = `${window.location.origin}${window.location.pathname}#radar?${params}`;
    try {
      await navigator.clipboard.writeText(link);
      announce("Link copiado para a área de transferência.");
      $("radar-share").textContent = "✓ Link copiado";
    } catch {
      $("radar-share").textContent = "Link na barra de endereço";
      window.history.replaceState(null, "", `#radar?${params}`);
      announce("Não foi possível copiar; o link está na barra de endereço.");
    }
    window.setTimeout(() => { $("radar-share").textContent = "🔗 Copiar link"; }, 2500);
  });
  ["filter-search", "filter-airline", "filter-level", "filter-alert"].forEach((id) => {
    $(id).addEventListener(id === "filter-search" ? "input" : "change", () => {
      if (!data) return;
      renderCards();
      renderView();
    });
  });
  document.addEventListener("themechange", () => data && drawMap(filteredAircraft()));
  return refresh();
}

export function onHide() {
  stopPlaying();
}

export function onShow() {
  if (map) window.setTimeout(() => map.invalidateSize(), 0);
}
