// Teoria: texto do catálogo (mesma fonte do laboratório).
import { clear, el, renderPseudocode, showError } from "./core.js";
import { algorithmById, getCatalog } from "./catalog.js";

const $ = (id) => document.getElementById(id);
let catalog = null;
let current = "closest_pair";

function render() {
  const a = algorithmById(catalog, current);
  document.querySelectorAll("#theory-nav button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === current)));
  const c = a.complexity;
  clear($("theory-content")).append(el("article", { class: "theory-card", "aria-labelledby": "theory-title" },
    el("h3", { id: "theory-title", text: a.name }),
    el("p", { text: a.problem }),
    el("dl", {},
      el("dt", { text: "Dividir" }), el("dd", { text: a.divide }),
      el("dt", { text: "Conquistar" }), el("dd", { text: a.conquer }),
      el("dt", { text: "Combinar" }), el("dd", { text: a.combine }),
      el("dt", { text: "Caso-base" }), el("dd", { text: a.base_case }),
      el("dt", { text: "Recorrência" }), el("dd", { class: "mono", text: a.recurrence }),
      el("dt", { text: "Teorema Mestre" }), el("dd", { text: a.master }),
      el("dt", { text: "Corretude" }), el("dd", { text: a.correctness }),
      el("dt", { text: "Limitações" }), el("dd", { text: a.limits }),
      el("dt", { text: "Operações contadas" }), el("dd", { text: a.unit }),
      el("dt", { text: "Referência" }), el("dd", { text: a.reference })),
    el("div", { class: "table-wrap" }, el("table", { class: "complexity" },
      el("caption", { text: "Complexidade" }),
      el("thead", {}, el("tr", {}, ["Melhor", "Médio", "Pior", "Espaço"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, el("tr", {}, [c.best, c.average, c.worst, c.space].map((v) => el("td", { text: v })))))),
    el("h4", { text: "Pseudocódigo" }),
    renderPseudocode(el("ol", { class: "pseudo" }), a.pseudocode, null),
    el("p", {}, a.id === "closest_pair"
      ? el("a", { href: "#visualizador", text: "Ver no visualizador →" })
      : el("a", { href: `#laboratorio?alg=${a.id}`, text: "Executar no laboratório →" })),
  ));
}

export async function init(params) {
  try {
    catalog = await getCatalog();
  } catch (error) {
    $("theory-content").append(el("div", { class: "banner error", role: "alert" }));
    showError($("theory-content").lastChild, error);
    return;
  }
  $("theory-nav").replaceChildren(...catalog.algorithms.map((a) => el("button", {
    type: "button", dataset: { id: a.id }, text: a.name,
    onclick: () => {
      current = a.id;
      render();
    },
  })));
  onShow(params);
  render();
}

export function onShow(params) {
  if (catalog && params.has("alg") && algorithmById(catalog, params.get("alg"))) {
    current = params.get("alg");
    render();
  }
}
