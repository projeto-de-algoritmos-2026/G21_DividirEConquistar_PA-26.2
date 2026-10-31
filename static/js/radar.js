const CRITICAL = "#e66767";
const NORMAL = "#7fb2ee";

const map = L.map("map", { worldCopyJump: true }).setView([-15, -50], 4);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap",
}).addTo(map);
const planesLayer = L.layerGroup().addTo(map);
const alertsLayer = L.layerGroup().addTo(map);

const controls = {
  source: document.getElementById("source"),
  count: document.getElementById("count"),
  seed: document.getElementById("seed"),
  minutes: document.getElementById("minutes"),
  minutesLabel: document.getElementById("minutes-label"),
  play: document.getElementById("play"),
};
let lastBands = [];
let playTimer = null;
let latestRequest = 0;

function trafficQuery() {
  return new URLSearchParams({
    source: controls.source.value,
    n: controls.count.value,
    seed: controls.seed.value,
    minutes: controls.minutes.value,
  });
}

function formatLevel(level) {
  return `FL${String(level).padStart(3, "0")}`;
}

function drawAircraft(aircraft) {
  planesLayer.clearLayers();
  aircraft.forEach((plane) => {
    L.circleMarker([plane.lat, plane.lon], {
      radius: 3, color: NORMAL, weight: 1, fillOpacity: 0.8,
    }).bindTooltip(`${plane.callsign} · ${Math.round(plane.altitude_ft)} ft`).addTo(planesLayer);
  });
}

function drawAlerts(bands) {
  alertsLayer.clearLayers();
  bands.filter((band) => band.alert).forEach((band) => {
    const [a, b] = band.pair;
    L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: CRITICAL, weight: 3 }).addTo(alertsLayer);
    [a, b].forEach((plane) => {
      L.circleMarker([plane.lat, plane.lon], {
        radius: 7, color: CRITICAL, weight: 2, fillOpacity: 0.3,
      }).addTo(alertsLayer);
    });
    L.marker([a.lat, a.lon], {
      icon: L.divIcon({
        className: "",
        html: `<span class="conflict-label">⚠ ${formatLevel(band.flight_level)} · ${band.distance_nm.toFixed(1)} NM</span>`,
        iconAnchor: [-10, 10],
      }),
    }).addTo(alertsLayer);
  });
}

function renderTable(bands) {
  const sorted = [...bands].sort((a, b) => a.distance_nm - b.distance_nm);
  lastBands = sorted;
  document.getElementById("bands").innerHTML = sorted.map((band, index) => `
    <tr data-index="${index}" class="${band.alert ? "alert" : ""}">
      <td>${band.alert ? "⚠ " : ""}${formatLevel(band.flight_level)}</td>
      <td>${band.aircraft_count}</td>
      <td>${band.pair[0].callsign} / ${band.pair[1].callsign}</td>
      <td>${band.distance_nm.toFixed(1)} NM</td>
    </tr>`).join("");
}

function renderSummary(aircraft, bands) {
  const alerts = bands.filter((band) => band.alert).length;
  const comparisons = bands.reduce((total, band) => total + band.comparisons, 0);
  const summary = document.getElementById("summary");
  summary.classList.toggle("alerting", alerts > 0);
  if (bands.length === 0) {
    summary.textContent = `${aircraft.length} aeronaves, nenhuma faixa com duas ou mais.`;
    return;
  }
  summary.textContent = `${alerts ? `⚠ ${alerts} conflito(s)` : "Sem conflitos"} · `
    + `${aircraft.length} aeronaves · ${comparisons.toLocaleString("pt-BR")} comparações`;
}

async function refresh() {
  const request = ++latestRequest;
  const response = await fetch(`/api/scan?${trafficQuery()}`);
  const { aircraft, bands } = await response.json();
  if (request !== latestRequest) return;  // resposta antiga chegou depois da nova
  drawAircraft(aircraft);
  drawAlerts(bands);
  renderTable(bands);
  renderSummary(aircraft, bands);
}

function stopPlaying() {
  clearInterval(playTimer);
  playTimer = null;
  controls.play.textContent = "Reproduzir";
}

function togglePlay() {
  if (playTimer) {
    stopPlaying();
    return;
  }
  controls.play.textContent = "Pausar";
  playTimer = setInterval(() => {
    const next = (Number(controls.minutes.value) + 1) % (Number(controls.minutes.max) + 1);
    controls.minutes.value = next;
    controls.minutesLabel.textContent = `${next} min`;
    refresh();
  }, 700);
}

function changed() {
  const isSimulation = controls.source.value === "sim";
  document.querySelectorAll(".sim-only").forEach((element) => {
    element.hidden = !isSimulation;
    element.style.display = isSimulation ? "" : "none";
  });
  if (!isSimulation) stopPlaying();
  controls.minutesLabel.textContent = `${controls.minutes.value} min`;
  refresh();
  document.dispatchEvent(new CustomEvent("trafficchange"));
}

document.getElementById("bands").addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-index]");
  if (!row) return;
  const [a, b] = lastBands[row.dataset.index].pair;
  map.fitBounds([[a.lat, a.lon], [b.lat, b.lon]], { maxZoom: 9, padding: [80, 80] });
});
[controls.source, controls.count, controls.seed].forEach((input) => input.addEventListener("change", changed));
controls.minutes.addEventListener("input", changed);
controls.play.addEventListener("click", togglePlay);
document.addEventListener("tabchange", (event) => {
  if (event.detail === "radar") map.invalidateSize();
});

changed();
