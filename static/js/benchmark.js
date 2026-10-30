const CHART = { width: 820, height: 380, left: 78, right: 24, top: 16, bottom: 48 };
const SERIES = [
  { key: "divide_ms", label: "Dividir e conquistar", color: "#3987e5" },
  { key: "brute_ms", label: "Força bruta", color: "#d95926" },
];
const runButton = document.getElementById("run-benchmark");

const log10Scale = (min, max, from, to) => (value) =>
  from + (Math.log10(value) - Math.log10(min)) / (Math.log10(max) - Math.log10(min)) * (to - from);

function powerTicks(min, max) {
  const ticks = [];
  for (let exponent = Math.floor(Math.log10(min)); 10 ** exponent <= max * 1.001; exponent += 1) {
    if (10 ** exponent >= min / 1.001) ticks.push(10 ** exponent);
  }
  return ticks;
}

function drawChart(rows) {
  const times = rows.flatMap((row) => SERIES.map((series) => row[series.key]));
  const yMin = 10 ** Math.floor(Math.log10(Math.min(...times)));
  const yMax = 10 ** Math.ceil(Math.log10(Math.max(...times)));
  const x = log10Scale(rows[0].n, rows[rows.length - 1].n, CHART.left, CHART.width - CHART.right);
  const y = log10Scale(yMin, yMax, CHART.height - CHART.bottom, CHART.top);
  const parts = [];

  powerTicks(yMin, yMax).forEach((tick) => {
    parts.push(`<line x1="${CHART.left}" x2="${CHART.width - CHART.right}" y1="${y(tick)}" y2="${y(tick)}" stroke="#2c363c"/>`);
    parts.push(`<text x="${CHART.left - 10}" y="${y(tick) + 4}" text-anchor="end" fill="#a9b1b5" font-size="12">${tick.toLocaleString("pt-BR")} ms</text>`);
  });
  rows.forEach((row) => {
    parts.push(`<text x="${x(row.n)}" y="${CHART.height - CHART.bottom + 22}" text-anchor="middle" fill="#a9b1b5" font-size="12">${row.n}</text>`);
  });
  parts.push(`<text x="${(CHART.left + CHART.width - CHART.right) / 2}" y="${CHART.height - 6}" text-anchor="middle" fill="#a9b1b5" font-size="12">Número de pontos (n)</text>`);

  SERIES.forEach((series) => {
    const path = rows.map((row) => `${x(row.n)},${y(row[series.key])}`).join(" ");
    parts.push(`<polyline points="${path}" fill="none" stroke="${series.color}" stroke-width="2"/>`);
    rows.forEach((row) => {
      const cx = x(row.n);
      const cy = y(row[series.key]);
      parts.push(`<circle cx="${cx}" cy="${cy}" r="4" fill="${series.color}" stroke="#0f1417" stroke-width="2"/>`);
      parts.push(`<circle class="hit" cx="${cx}" cy="${cy}" r="14" fill="transparent"
        data-label="${series.label}" data-n="${row.n}" data-value="${row[series.key].toFixed(2)}"/>`);
    });
  });

  SERIES.forEach((series) => {
    parts.push(`<text x="${x(rows[1].n)}" y="${y(rows[1][series.key]) - 12}" text-anchor="middle" fill="#f0efec" font-size="12">${series.label}</text>`);
  });

  const last = rows[rows.length - 1];
  const ratio = Math.round(last.brute_ms / last.divide_ms);
  parts.push(`<text x="${x(last.n) - 8}" y="${y(last.brute_ms) - 12}" text-anchor="end" fill="#f0efec" font-size="13">${ratio}× mais lenta em n = ${last.n}</text>`);

  document.getElementById("chart").innerHTML =
    `<svg viewBox="0 0 ${CHART.width} ${CHART.height}" role="img" aria-label="Tempo de execução por número de pontos, em escala logarítmica">${parts.join("")}</svg>`;
}

function drawTable(rows) {
  const table = document.getElementById("benchmark-table");
  table.hidden = false;
  table.querySelector("tbody").innerHTML = rows.map((row) => `
    <tr>
      <td>${row.n}</td>
      <td>${row.divide_ms.toFixed(2)}</td>
      <td>${row.brute_ms.toFixed(2)}</td>
      <td>${row.divide_comparisons.toLocaleString("pt-BR")}</td>
      <td>${row.brute_comparisons.toLocaleString("pt-BR")}</td>
    </tr>`).join("");
}

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  runButton.textContent = "Executando…";
  const { rows } = await (await fetch("/api/benchmark")).json();
  drawChart(rows);
  drawTable(rows);
  document.getElementById("legend").hidden = false;
  runButton.disabled = false;
  runButton.textContent = "Executar novamente";
});

document.addEventListener("tabchange", (event) => {
  // O benchmark usa pontos próprios, então os controles de tráfego não se aplicam.
  document.querySelector(".controls").style.display = event.detail === "benchmark" ? "none" : "";
});

const tooltip = document.getElementById("tooltip");
document.getElementById("chart").addEventListener("mousemove", (event) => {
  const hit = event.target.closest(".hit");
  tooltip.hidden = !hit;
  if (!hit) return;
  const box = tooltip.parentElement.getBoundingClientRect();
  tooltip.textContent = `${hit.dataset.label}: ${hit.dataset.value} ms (n = ${hit.dataset.n})`;
  const left = event.clientX - box.left + 14;
  tooltip.style.left = `${Math.min(left, box.width - tooltip.offsetWidth - 8)}px`;
  tooltip.style.top = `${event.clientY - box.top + 14}px`;
});
