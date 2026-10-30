const svg = document.getElementById("steps-svg");
const stepRange = document.getElementById("step-range");
const stepPlay = document.getElementById("step-play");
const WIDTH = 800;
const HEIGHT = 520;
const PADDING = 26;
const BLEED = 600;  // as faixas ocupam toda a altura, mesmo fora do viewBox
const STEP_LABELS = {
  divide: "Dividir",
  base: "Caso base",
  combine: "Combinar",
};

let trace = null;
let current = 0;
let stepTimer = null;
let scaleX = null;
let scaleY = null;

function buildScales(points) {
  const xs = points.map((point) => point[0]);
  const ys = points.map((point) => point[1]);
  const [minX, maxX] = [Math.min(...xs), Math.max(...xs)];
  const [minY, maxY] = [Math.min(...ys), Math.max(...ys)];
  scaleX = (x) => PADDING + (x - minX) / (maxX - minX || 1) * (WIDTH - 2 * PADDING);
  scaleY = (y) => HEIGHT - PADDING - (y - minY) / (maxY - minY || 1) * (HEIGHT - 2 * PADDING);
}

function stepText(step) {
  const distance = step.distance === null ? "nenhum par ainda" : `${step.distance.toFixed(1)} km`;
  if (step.kind === "divide") {
    return `Divide ${step.size} pontos pela mediana de x, x = ${step.middle_x.toFixed(0)} km. `
      + `Profundidade ${step.depth}. Melhor até agora: ${distance}.`;
  }
  if (step.kind === "base") {
    return `Com ${step.size} ponto(s), compara todos os pares diretamente. Melhor até agora: ${distance}.`;
  }
  return `Olha os ${step.strip.length} ponto(s) a menos de δ da divisão, em ordem de y, `
    + `para achar pares que cruzam as metades. δ = ${distance}.`;
}

function drawStep() {
  const step = trace.steps[current];
  const parts = [`<rect x="${scaleX(step.low_x)}" y="${-BLEED}" width="${Math.max(scaleX(step.high_x) - scaleX(step.low_x), 2)}"
    height="${HEIGHT + 2 * BLEED}" fill="#3987e5" opacity="0.13"/>`];

  if (step.middle_x !== null) {
    const x = scaleX(step.middle_x);
    if (step.kind === "combine" && step.distance !== null) {
      const left = scaleX(step.middle_x - step.distance);
      const right = scaleX(step.middle_x + step.distance);
      parts.push(`<rect x="${left}" y="${-BLEED}" width="${right - left}" height="${HEIGHT + 2 * BLEED}" fill="#eda100" opacity="0.16"/>`);
    }
    parts.push(`<line x1="${x}" x2="${x}" y1="${-BLEED}" y2="${HEIGHT + BLEED}" stroke="#f0efec" stroke-dasharray="6 5"/>`);
  }

  trace.points.forEach((point, index) => {
    const inStrip = step.strip.includes(index);
    parts.push(`<circle cx="${scaleX(point[0])}" cy="${scaleY(point[1])}" r="${inStrip ? 6 : 4.5}"
      fill="${inStrip ? "#eda100" : "#a9b1b5"}" stroke="#182025" stroke-width="2"/>`);
  });

  const [a, b] = step.best;
  if (a >= 0) {
    const [pa, pb] = [trace.points[a], trace.points[b]];
    parts.push(`<line x1="${scaleX(pa[0])}" y1="${scaleY(pa[1])}" x2="${scaleX(pb[0])}" y2="${scaleY(pb[1])}"
      stroke="#e66767" stroke-width="3"/>`);
    [pa, pb].forEach((point) => {
      parts.push(`<circle cx="${scaleX(point[0])}" cy="${scaleY(point[1])}" r="6" fill="#e66767" stroke="#182025" stroke-width="2"/>`);
    });
  }

  svg.innerHTML = parts.join("");
  document.getElementById("step-title").textContent =
    `${STEP_LABELS[step.kind]} · ${current + 1} de ${trace.steps.length} · FL${trace.flight_level}`;
  document.getElementById("step-text").textContent = stepText(step);
  stepRange.value = current;
}

function goTo(index) {
  if (!trace) return;
  current = Math.max(0, Math.min(trace.steps.length - 1, index));
  drawStep();
}

function stopSteps() {
  clearInterval(stepTimer);
  stepTimer = null;
  stepPlay.textContent = "Reproduzir";
}

async function loadTrace() {
  stopSteps();
  const response = await fetch(`/api/steps?${trafficQuery()}`);
  const data = await response.json();
  if (!response.ok) {
    trace = null;
    svg.innerHTML = "";
    document.getElementById("step-text").textContent = data.error;
    return;
  }
  trace = data;
  buildScales(trace.points);
  stepRange.max = trace.steps.length - 1;
  goTo(0);
}

document.getElementById("step-prev").addEventListener("click", () => goTo(current - 1));
document.getElementById("step-next").addEventListener("click", () => goTo(current + 1));
stepRange.addEventListener("input", () => goTo(Number(stepRange.value)));
stepPlay.addEventListener("click", () => {
  if (stepTimer) {
    stopSteps();
    return;
  }
  stepPlay.textContent = "Pausar";
  stepTimer = setInterval(() => {
    if (current >= trace.steps.length - 1) stopSteps();
    else goTo(current + 1);
  }, 700);
});
document.addEventListener("tabchange", (event) => {
  if (event.detail === "steps") loadTrace();
});
document.addEventListener("trafficchange", () => {
  if (document.getElementById("tab-steps").classList.contains("active")) loadTrace();
});
