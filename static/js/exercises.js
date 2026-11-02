// Exercícios: enunciado gerado por seed; correção feita no servidor.
import { announce, api, clear, el, isAbort, readInt, showError } from "./core.js";

const $ = (id) => document.getElementById(id);
let exercise = null;

async function load() {
  const node = $("ex-answer-form");
  let seed;
  try {
    seed = readInt($("ex-seed"), "Seed");
  } catch (error) {
    clear(node).append(el("div", { class: "banner error", role: "alert", text: error.message }));
    return;
  }
  try {
    exercise = await api(`/api/exercises/new?type=${$("ex-type").value}&seed=${seed}`, { key: "exercise" });
    render();
  } catch (error) {
    if (isAbort(error)) return;
    clear(node).append(el("div", { class: "banner error", role: "alert" }));
    showError(node.lastChild, error);
  }
}

function render() {
  const node = clear($("ex-answer-form"));
  node.append(el("h3", { text: `${exercise.title} · seed ${exercise.seed}` }), el("p", { text: exercise.enunciado }));
  if (exercise.values) {
    node.append(el("div", { class: "values", "aria-label": "Vetor" }, exercise.values.map((v, i) => el("span", { title: `posição ${i}`, text: String(v) }))));
  }
  if (exercise.answer_type === "option") {
    node.append(el("fieldset", { class: "options" },
      el("legend", { class: "sr-only", text: "Alternativas" }),
      exercise.options.map((option, index) => el("label", {},
        el("input", { type: "radio", name: "ex-option", value: String(index), required: index === 0 }), option))));
  } else {
    node.append(el("label", { class: "field", style: { maxWidth: "220px" } }, "Sua resposta",
      el("input", { id: "ex-answer", type: "number", step: "1", required: true, inputmode: "numeric" })));
  }
  node.append(
    el("div", { class: "segmented", style: { marginTop: "10px" } }, el("button", { class: "primary", type: "submit", text: "Verificar" })),
    el("div", { id: "ex-feedback", style: { marginTop: "12px" } }),
  );
}

async function check(event) {
  event.preventDefault();
  if (!exercise) return;
  const feedback = $("ex-feedback");
  let answer;
  if (exercise.answer_type === "option") {
    const chosen = document.querySelector("input[name=ex-option]:checked");
    answer = chosen ? Number(chosen.value) : null;
  } else {
    const input = $("ex-answer");
    answer = input.value.trim() === "" ? null : Number(input.value);
    input.setAttribute("aria-invalid", Number.isInteger(answer) ? "false" : "true");
  }
  if (!Number.isInteger(answer)) {
    clear(feedback).append(el("div", { class: "banner warn", role: "alert", text: "Informe uma resposta inteira ou escolha uma alternativa." }));
    return;
  }
  try {
    const result = await api("/api/exercises/check", { method: "POST", body: { type: exercise.type, seed: exercise.seed, answer } });
    const expected = exercise.answer_type === "option" ? exercise.options[result.expected] : String(result.expected);
    clear(feedback).append(el("div", { class: `banner ${result.correct ? "ok" : "error"}` },
      el("span", {}, el("strong", { text: result.correct ? "Correto! " : `Ainda não. Resposta: ${expected}. ` }), result.explanation)));
    announce(result.correct ? "Resposta correta." : `Resposta incorreta. O esperado era ${expected}.`);
  } catch (error) {
    clear(feedback).append(el("div", { class: "banner error", role: "alert", text: error.message }));
  }
}

export function init() {
  $("ex-form").addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });
  $("ex-type").addEventListener("change", load);
  $("ex-random").addEventListener("click", () => {
    $("ex-seed").value = String(Math.floor(Math.random() * 1_000_000));
    load();
  });
  $("ex-answer-form").addEventListener("submit", check);
  return load();
}
