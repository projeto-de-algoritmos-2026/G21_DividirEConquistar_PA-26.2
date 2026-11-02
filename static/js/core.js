// Utilitários compartilhados: DOM seguro (sem innerHTML com dados), API, tabelas e player de etapas.

const SVG_NS = "http://www.w3.org/2000/svg";

function apply(node, attrs) {
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "text") node.textContent = value;
    else if (key === "class") node.setAttribute("class", value);
    else if (key === "style" && typeof value === "object") Object.assign(node.style, value);
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else if (key === "dataset") Object.assign(node.dataset, value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  return node;
}

function append(node, children) {
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

export function el(tag, attrs, ...children) {
  return append(apply(document.createElement(tag), attrs), children);
}

export function svg(tag, attrs, ...children) {
  // Cores com var(--token) vão para o style: atributos de apresentação não resolvem var() em todo navegador.
  const plain = { ...attrs };
  const style = [];
  for (const key of ["fill", "stroke"]) {
    if (typeof plain[key] === "string" && plain[key].startsWith("var(")) {
      style.push(`${key}:${plain[key]}`);
      delete plain[key];
    }
  }
  if (style.length) plain.style = [plain.style, ...style].filter(Boolean).join(";");
  return append(apply(document.createElementNS(SVG_NS, tag), plain), children);
}

export function clear(node) {
  node.replaceChildren();
  return node;
}

/** Substitui o conteúdo ignorando null/false (o append nativo escreveria "null"). */
export function fill(node, ...children) {
  node.replaceChildren();
  return append(node, children);
}

const numberFormats = new Map();
export function fmt(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (!numberFormats.has(digits)) {
    numberFormats.set(digits, new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits }));
  }
  return numberFormats.get(digits).format(value);
}

export function fmtMs(value) {
  if (value === null || value === undefined) return "—";
  if (value < 0.1) return `${fmt(value * 1000, 0)} µs`;
  return `${fmt(value, value < 10 ? 2 : 1)} ms`;
}

export function flightLevel(level) {
  return `FL${String(level).padStart(3, "0")}`;
}

export const storage = {
  get(key) {
    try { return localStorage.getItem(key); } catch { return null; }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); } catch { /* armazenamento indisponível */ }
  },
};

const announcer = () => document.getElementById("announcer");
export function announce(message) {
  const node = announcer();
  node.textContent = "";
  // Pequeno atraso para leitores de tela perceberem a troca.
  window.setTimeout(() => { node.textContent = message; }, 30);
}

export class ApiError extends Error {}

const controllers = new Map();

/** Chamada à API. Com `key`, uma nova chamada cancela a anterior de mesma chave. */
export async function api(path, { method = "GET", body, key } = {}) {
  let controller = null;
  if (key) {
    controllers.get(key)?.abort();
    controller = new AbortController();
    controllers.set(key, controller);
  }
  const aborted = () => new DOMException("cancelado", "AbortError");
  try {
    let response;
    try {
      response = await fetch(path, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller?.signal,
      });
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new ApiError("Falha de rede: o servidor local não respondeu. Verifique se o app está em execução.");
    }
    let data;
    try {
      data = await response.json();
    } catch (error) {
      if (controller?.signal.aborted) throw aborted();
      throw new ApiError(`Resposta inválida do servidor (HTTP ${response.status}).`);
    }
    if (controller?.signal.aborted) throw aborted();
    if (!response.ok) throw new ApiError(data?.error || `Erro HTTP ${response.status}.`);
    return data;
  } finally {
    if (key && controllers.get(key) === controller) controllers.delete(key);
  }
}

export const isAbort = (error) => error?.name === "AbortError";

export function showError(node, error) {
  if (!error) {
    node.hidden = true;
    node.textContent = "";
    return;
  }
  node.hidden = false;
  node.textContent = error.message || String(error);
  announce(`Erro: ${node.textContent}`);
}

export function setBusy(form, busy, label) {
  form.setAttribute("aria-busy", busy ? "true" : "false");
  const submit = form.querySelector("button[type=submit]");
  if (submit) {
    if (!submit.dataset.label) submit.dataset.label = submit.textContent;
    submit.disabled = busy;
    submit.textContent = busy ? (label || "Executando…") : submit.dataset.label;
  }
}

/** Lê um inteiro de um input e marca aria-invalid quando fora dos limites. */
export function readInt(input, label) {
  const value = Number(input.value);
  const min = input.min === "" ? -Infinity : Number(input.min);
  const max = input.max === "" ? Infinity : Number(input.max);
  const ok = input.value.trim() !== "" && Number.isInteger(value) && value >= min && value <= max;
  input.setAttribute("aria-invalid", ok ? "false" : "true");
  if (!ok) throw new ApiError(`${label}: informe um inteiro entre ${fmt(min)} e ${fmt(max)}.`);
  return value;
}

export function readFloat(input, label) {
  const value = Number(input.value);
  const min = Number(input.min);
  const max = Number(input.max);
  const ok = input.value.trim() !== "" && Number.isFinite(value) && value >= min && value <= max;
  input.setAttribute("aria-invalid", ok ? "false" : "true");
  if (!ok) throw new ApiError(`${label}: informe um número entre ${fmt(min, 1)} e ${fmt(max, 1)}.`);
  return value;
}

/**
 * Tabela ordenável. `columns`: [{key, label, value(row), render(row)?, num?}].
 * Retorna {element, update(rows), select(key)}.
 */
export function sortableTable({ columns, caption, rowKey, onRowClick, rowClass, sort = null, empty = "Nada a mostrar." }) {
  let rows = [];
  let state = sort;
  let selected = null;
  const thead = el("thead");
  const tbody = el("tbody");
  const table = el("table", {}, caption ? el("caption", { text: caption }) : null, thead, tbody);

  function header() {
    clear(thead).append(el("tr", {}, columns.map((column) => {
      const direction = state?.key === column.key ? (state.dir > 0 ? "ascending" : "descending") : null;
      return el("th", { scope: "col", class: column.num ? "num" : null, "aria-sort": direction || "none" },
        el("button", {
          type: "button", class: "sort", text: column.label,
          onclick: () => {
            state = { key: column.key, dir: state?.key === column.key ? -state.dir : 1 };
            render();
          },
        }));
    })));
  }

  function render() {
    header();
    clear(tbody);
    const ordered = [...rows];
    if (state) {
      const column = columns.find((item) => item.key === state.key);
      ordered.sort((a, b) => {
        const x = column.value(a);
        const y = column.value(b);
        if (x === y) return 0;
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return (x < y ? -1 : 1) * state.dir;
      });
    }
    if (!ordered.length) {
      tbody.append(el("tr", {}, el("td", { colspan: columns.length, class: "empty", text: empty })));
      return;
    }
    for (const row of ordered) {
      const key = rowKey ? rowKey(row) : null;
      const tr = el("tr", {
        class: [onRowClick ? "clickable" : "", rowClass ? rowClass(row) : ""].join(" ").trim() || null,
        "aria-selected": onRowClick ? String(key === selected) : null,
        tabindex: onRowClick ? "0" : null,
      }, columns.map((column) => el("td", { class: column.num ? "num" : null },
        column.render ? column.render(row) : String(column.value(row) ?? "—"))));
      if (onRowClick) {
        tr.addEventListener("click", () => onRowClick(row));
        tr.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onRowClick(row);
          }
        });
      }
      tbody.append(tr);
    }
  }

  return {
    element: table,
    update(next) { rows = next; render(); },
    select(key) { selected = key; render(); },
  };
}

/** Renderiza o pseudocódigo e destaca a linha `current` (1-based). */
export function renderPseudocode(list, lines, current) {
  clear(list);
  lines.forEach((line, index) => {
    // O alinhamento dos comentários (▹) no catálogo só serve ao texto puro; aqui quebraria a linha.
    list.append(el("li", { "aria-current": index + 1 === current ? "true" : null, text: line.replace(/\s{2,}▹/, "   ▹") }));
  });
  return list;
}

/**
 * Player de etapas: início, anterior, reproduzir/pausar, próxima, fim,
 * barra de progresso e velocidade. Teclado no elemento `stage`.
 */
export class Player {
  constructor(container, stage, onRender) {
    this.onRender = onRender;
    this.count = 0;
    this.index = 0;
    this.timer = null;
    const button = (text, label, action) => el("button", { type: "button", class: "icon", "aria-label": label, title: label, text, onclick: action });
    this.first = button("⏮", "Primeira etapa", () => this.go(0));
    this.prev = button("◀", "Etapa anterior", () => this.go(this.index - 1));
    this.play = button("▶", "Reproduzir", () => this.toggle());
    this.next = button("▶|", "Próxima etapa", () => this.go(this.index + 1));
    this.last = button("⏭", "Última etapa", () => this.go(this.count - 1));
    this.speed = el("select", { "aria-label": "Velocidade" },
      el("option", { value: "1400", text: "0,5×" }),
      el("option", { value: "700", text: "1×", selected: true }),
      el("option", { value: "300", text: "2×" }),
      el("option", { value: "120", text: "5×" }));
    this.range = el("input", { type: "range", min: "0", max: "0", value: "0", "aria-label": "Progresso das etapas" });
    this.counter = el("span", { class: "small muted", "aria-hidden": "true" });
    this.range.addEventListener("input", () => this.go(Number(this.range.value)));
    container.replaceChildren(el("div", { class: "player" },
      el("div", { class: "player-buttons" }, this.first, this.prev, this.play, this.next, this.last, this.speed, this.counter),
      this.range));
    stage.addEventListener("keydown", (event) => {
      if (event.target !== stage) return;
      const actions = {
        ArrowLeft: () => this.go(this.index - 1),
        ArrowRight: () => this.go(this.index + 1),
        Home: () => this.go(0),
        End: () => this.go(this.count - 1),
        " ": () => this.toggle(),
      };
      if (actions[event.key]) {
        event.preventDefault();
        actions[event.key]();
      }
    });
    this.load(0);
  }

  load(count) {
    this.stop();
    this.count = count;
    this.range.max = String(Math.max(0, count - 1));
    this.go(0);
  }

  go(index) {
    if (!this.count) {
      this.index = 0;
      this.sync();
      return;
    }
    this.index = Math.max(0, Math.min(this.count - 1, index));
    this.sync();
    this.onRender(this.index);
  }

  sync() {
    const empty = this.count === 0;
    [this.first, this.prev].forEach((b) => { b.disabled = empty || this.index === 0; });
    [this.next, this.last].forEach((b) => { b.disabled = empty || this.index >= this.count - 1; });
    this.play.disabled = empty;
    this.range.disabled = empty;
    this.range.value = String(this.index);
    this.range.setAttribute("aria-valuetext", empty ? "sem etapas" : `etapa ${this.index + 1} de ${this.count}`);
    this.counter.textContent = empty ? "" : `${this.index + 1} / ${this.count}`;
  }

  toggle() {
    if (this.timer) {
      this.stop();
      return;
    }
    if (this.index >= this.count - 1) this.go(0);
    this.play.textContent = "⏸";
    this.play.setAttribute("aria-label", "Pausar");
    const tick = () => {
      if (this.index >= this.count - 1) {
        this.stop();
        return;
      }
      this.go(this.index + 1);
      this.timer = window.setTimeout(tick, Number(this.speed.value));
    };
    this.timer = window.setTimeout(tick, Number(this.speed.value));
  }

  stop() {
    window.clearTimeout(this.timer);
    this.timer = null;
    this.play.textContent = "▶";
    this.play.setAttribute("aria-label", "Reproduzir");
  }
}

/** Baixa um texto como arquivo, sem servidor. */
export function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = el("a", { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Escala linear [d0, d1] → [r0, r1], tolerante a domínio degenerado. */
export function linear(d0, d1, r0, r1) {
  const span = d1 - d0 || 1;
  return (value) => r0 + ((value - d0) / span) * (r1 - r0);
}

export const SCENARIO_TYPE = "radar-dc-cenario";
export const SCENARIO_MAX_BYTES = 256 * 1024;

/** Lê um arquivo JSON local (nada é enviado a serviços externos), com limite de tamanho. */
export async function readJsonFile(file) {
  if (!file) throw new ApiError("Nenhum arquivo selecionado.");
  if (file.size > SCENARIO_MAX_BYTES) throw new ApiError("Arquivo grande demais (limite de 256 KB).");
  let data;
  try {
    data = JSON.parse(await file.text());
  } catch {
    throw new ApiError("O arquivo não é um JSON válido.");
  }
  if (!data || typeof data !== "object" || Array.isArray(data) || data.tipo !== SCENARIO_TYPE || data.versao !== 1) {
    throw new ApiError(`JSON não reconhecido: esperado {"tipo": "${SCENARIO_TYPE}", "versao": 1, …}.`);
  }
  return data;
}

/** Botões “Exportar cenário” e “Importar cenário” (input de arquivo acessível). */
export function scenarioTools({ id, onExport, onImport }) {
  const input = el("input", { id: `${id}-file`, type: "file", accept: "application/json,.json", class: "sr-only" });
  input.addEventListener("change", async () => {
    const [file] = input.files;
    input.value = "";
    if (file) await onImport(file);
  });
  return el("div", { class: "segmented scenario-tools", role: "group", "aria-label": "Cenário em JSON" },
    el("button", { type: "button", id: `${id}-export`, text: "⬇ Exportar cenário", onclick: onExport }),
    el("label", { class: "file-button", for: `${id}-file`, tabindex: "0", role: "button",
      onkeydown: (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); input.click(); } } },
    "⬆ Importar cenário"),
    input);
}
