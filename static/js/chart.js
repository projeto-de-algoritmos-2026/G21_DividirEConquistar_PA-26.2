// Gráfico de linhas em escala log-log (SVG), tolerante a pontos ausentes, zero e um único n.
import { el, fmt, svg } from "./core.js";

const BOX = { width: 560, height: 336, left: 70, right: 16, top: 34, bottom: 46 };

function logScale(min, max, from, to) {
  const lo = Math.log10(min);
  const hi = Math.log10(max);
  if (hi - lo < 1e-9) return () => (from + to) / 2;
  return (value) => from + ((Math.log10(value) - lo) / (hi - lo)) * (to - from);
}

function ticks(min, max) {
  const out = [];
  for (let e = Math.floor(Math.log10(min)); 10 ** e <= max * 1.0001; e += 1) {
    if (10 ** e >= min / 1.0001) out.push(10 ** e);
  }
  return out.length ? out : [min];
}

/**
 * series: [{label, className, points: [{x, y, low?, high?}]}] — y nulo é ignorado.
 * Valores ≤ 0 (abaixo da resolução do relógio) são desenhados no piso e anotados.
 */
export function logLogChart({ title, yLabel, series, format = (v) => fmt(v, 2) }) {
  const all = series.flatMap((s) => s.points.filter((p) => p.y !== null && p.y !== undefined));
  if (!all.length) return el("p", { class: "empty", text: "Sem pontos para desenhar." });
  const positives = all.flatMap((p) => [p.y, p.low, p.high]).filter((v) => v > 0);
  const floor = positives.length ? Math.min(...positives) : 1e-3;
  const yMin = 10 ** Math.floor(Math.log10(floor));
  const yMax = 10 ** Math.ceil(Math.log10(Math.max(floor * 1.0001, ...positives)));
  const xs = all.map((p) => p.x);
  const x = logScale(Math.min(...xs), Math.max(...xs), BOX.left + 10, BOX.width - BOX.right - 10);
  const y = logScale(yMin, yMax === yMin ? yMin * 10 : yMax, BOX.height - BOX.bottom, BOX.top);
  const clamp = (v) => Math.max(v, floor);
  const root = svg("svg", { viewBox: `0 0 ${BOX.width} ${BOX.height}`, role: "img", "aria-label": `${title}, escala logarítmica nos dois eixos` });

  for (const tick of ticks(yMin, yMax)) {
    root.append(svg("line", { class: "grid", x1: BOX.left, x2: BOX.width - BOX.right, y1: y(tick), y2: y(tick) }));
    root.append(svg("text", { x: BOX.left - 8, y: y(tick) + 4, "text-anchor": "end", text: format(tick) }));
  }
  for (const value of [...new Set(xs)]) {
    root.append(svg("text", { x: x(value), y: BOX.height - BOX.bottom + 18, "text-anchor": "middle", text: fmt(value) }));
  }
  root.append(svg("text", { x: (BOX.left + BOX.width) / 2, y: BOX.height - 8, "text-anchor": "middle", text: "n (escala log)" }));
  root.append(svg("text", { x: 8, y: 14, text: yLabel }));

  for (const s of series) {
    const points = s.points.filter((p) => p.y !== null && p.y !== undefined);
    if (points.length > 1) {
      root.append(svg("polyline", { class: s.className, style: "fill:none", "stroke-width": 2.2, points: points.map((p) => `${x(p.x)},${y(clamp(p.y))}`).join(" ") }));
    }
    for (const p of points) {
      if (p.low !== undefined && p.high !== undefined && p.high > p.low) {
        root.append(svg("line", { class: s.className, x1: x(p.x), x2: x(p.x), y1: y(clamp(p.low)), y2: y(clamp(p.high)), "stroke-width": 1.5 }));
      }
      root.append(svg("circle", { class: s.className, cx: x(p.x), cy: y(clamp(p.y)), r: 4.5 },
        svg("title", { text: `${s.label}: ${format(p.y)} (n = ${fmt(p.x)})${p.y <= 0 ? " — abaixo da resolução do relógio" : ""}` })));
    }
  }
  return el("figure", { class: "chart", style: { margin: 0 } },
    root,
    el("figcaption", { class: "legend-row" }, series.map((s) => el("span", {},
      el("i", { class: "swatch", style: { background: s.className === "series-dc" ? "var(--accent)" : "var(--reference)" } }), s.label))));
}
