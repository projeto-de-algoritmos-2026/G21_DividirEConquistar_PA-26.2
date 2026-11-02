// Navegação por hash (#visao-geral, #radar?n=400…), tema e carregamento sob demanda das seções.
import { announce, el, fmt, storage } from "./core.js";
import { getCatalog } from "./catalog.js";

const VIEWS = {
  "visao-geral": { title: "Visão geral", load: () => import("./overview.js") },
  radar: { title: "Radar", load: () => import("./radar.js") },
  visualizador: { title: "Visualizador", load: () => import("./visualizer.js") },
  laboratorio: { title: "Laboratório", load: () => import("./lab.js") },
  comparacao: { title: "Comparação", load: () => import("./compare.js") },
  benchmarks: { title: "Benchmarks", load: () => import("./benchmark.js") },
  teoria: { title: "Teoria", load: () => import("./theory.js") },
  exercicios: { title: "Exercícios", load: () => import("./exercises.js") },
  ajuda: { title: "Ajuda", load: () => Promise.resolve({ init: initHelp }) },
};
const modules = new Map();
let current = null;

function parseHash() {
  const raw = decodeURIComponent(window.location.hash.slice(1));
  const [name, query = ""] = raw.split("?");
  return { name: VIEWS[name] ? name : "visao-geral", params: new URLSearchParams(query) };
}

async function route() {
  const { name, params } = parseHash();
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.viewPanel !== name;
  });
  document.querySelectorAll(".nav a").forEach((link) => {
    if (link.dataset.view === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  document.title = `${VIEWS[name].title} — Radar de Conflitos Aéreos`;
  const changed = current !== name;
  // Ao sair de uma seção, ela para timers (reprodução) para não seguir buscando dados escondida.
  if (changed && current) modules.get(current)?.onHide?.();
  current = name;
  if (changed) announce(`Seção ${VIEWS[name].title}`);

  let module = modules.get(name);
  if (!module) {
    module = await VIEWS[name].load();
    modules.set(name, module);
    await module.init?.(params);
  }
  module.onShow?.(params);
  if (changed) document.querySelector(`.nav a[data-view="${name}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function initTheme() {
  const button = document.getElementById("theme-toggle");
  const sync = () => {
    const dark = document.documentElement.dataset.theme !== "light";
    button.setAttribute("aria-pressed", String(!dark));
    button.title = dark ? "Usar tema claro" : "Usar tema escuro";
  };
  button.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    storage.set("theme", next);
    sync();
    document.dispatchEvent(new CustomEvent("themechange"));
    announce(next === "light" ? "Tema claro" : "Tema escuro");
  });
  sync();
}

async function initHelp() {
  const node = document.getElementById("help-limits");
  try {
    const { limits } = await getCatalog();
    node.replaceChildren(
      el("span", { text: `Radar: 2 a 3.000 aeronaves simuladas, minuto 0 a 240, limiar 0,5 a 20 NM. ` }),
      el("span", { text: `Visualizador: até ${limits.trace_max_n} pontos. Laboratório: passo a passo até ${limits.trace_max_n} elementos e execução até ${fmt(limits.lab_max_n)}. ` }),
      el("span", { text: `Comparação: n até ${fmt(limits.compare_max_n)}. Benchmark: até ${limits.bench_max_sizes} tamanhos, ${limits.bench_max_repeats} repetições, n até ${fmt(limits.bench_max_n)}; referências Θ(n²) só até n = ${fmt(limits.reference_max_n)}; um benchmark por vez e orçamento de 20 s.` }),
    );
  } catch (error) {
    node.textContent = `Não foi possível carregar os limites: ${error.message}`;
  }
}

initTheme();
window.addEventListener("hashchange", route);
route().catch((error) => {
  console.error(error);
  announce(`Erro ao abrir a seção: ${error.message}`);
});
