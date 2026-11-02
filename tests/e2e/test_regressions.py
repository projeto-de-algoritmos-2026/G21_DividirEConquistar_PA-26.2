"""Testes de interface: Visão geral, textos removidos, robustez de rede, cenários JSON e acessibilidade.

Rode com  pytest -m e2e  (ver conftest.py).
"""
import json
import re

import pytest

from tests.e2e.conftest import ENGINE, VIEWS, open_view

pytestmark = pytest.mark.e2e

OVERVIEW_MODULES = ["radar", "visualizador", "laboratorio", "comparacao", "benchmarks", "teoria", "exercicios", "ajuda"]
REMOVED_TEXTS = ["Aviso importante", "decisões operacionais", "radar certificado", "demonstrador acadêmico"]
INVALID_VALUE = re.compile(r"\b(null|undefined|NaN)\b")


# ---------------- Visão geral ----------------

def test_overview_offers_every_module_and_each_shortcut_navigates(page, base_url):
    open_view(page, base_url, "visao-geral")
    page.wait_for_load_state("networkidle")
    links = page.locator("#view-visao-geral .module").all()
    assert sorted(link.get_attribute("href") for link in links) == sorted(f"#{m}" for m in OVERVIEW_MODULES)
    for module in OVERVIEW_MODULES:
        page.click(f"#view-visao-geral .module[href='#{module}']")
        page.wait_for_selector(f"[data-view-panel='{module}']:not([hidden])")
        assert page.locator(f".nav a[data-view='{module}']").get_attribute("aria-current") == "page"
        page.go_back()  # o botão voltar do navegador devolve à Visão geral
        page.wait_for_selector("[data-view-panel='visao-geral']:not([hidden])")
        page.wait_for_load_state("networkidle")  # respostas atrasadas da seção anterior não mudam a URL
        assert page.url.endswith("#visao-geral")
    for href in ("#radar", "#visualizador", "#laboratorio", "#benchmarks"):
        assert page.locator(f"#view-visao-geral .route a[href='{href}']").count() == 1
    assert page.errors == []


def test_overview_kpis_match_a_real_scan(page, base_url):
    open_view(page, base_url, "visao-geral")
    page.wait_for_selector("#overview-kpis:not(.loading) .card")
    query = page.get_attribute("#overview-radar-link", "href").split("?", 1)[1]
    summary = page.request.get(f"{base_url}api/scan?{query}").json()["summary"]
    values = page.locator("#overview-kpis .card .value").all_inner_texts()
    assert values[0] == str(summary["bands_analyzed"])
    assert values[1] == str(summary["bands_below_threshold"])
    assert values[3].replace(".", "") == str(summary["comparisons"] + summary["candidate_pairs"])
    assert int(values[4]) == len(page.request.get(f"{base_url}api/lab/catalog").json()["algorithms"])
    status = page.inner_text("#overview-status")
    assert "Snapshot histórico" in status and "01/11/2026" in status
    page.click("#overview-radar-link")
    page.wait_for_selector("#radar-cards .card")
    assert "seed 21" in page.inner_text("#radar-source-banner")


def test_overview_reports_api_failures_without_broken_cards(page, base_url):
    page.route("**/api/health", lambda route: route.abort())
    page.route("**/api/scan**", lambda route: route.fulfill(status=503, json={"error": "falha simulada"}))
    open_view(page, base_url, "visao-geral")
    page.wait_for_selector("#overview-kpis .banner.error")
    assert "falha simulada" in page.inner_text("#overview-kpis")
    page.wait_for_selector("#overview-status .status-pill.bad")
    assert "indisponível" in page.inner_text("#overview-status")
    assert not INVALID_VALUE.search(page.inner_text("#view-visao-geral"))


def test_removed_warnings_are_absent_from_every_view(browser, base_url):
    for width in (1366, 390):
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        for view in VIEWS:
            open_view(page, base_url, view)
            page.wait_for_load_state("networkidle")
            html = page.content()  # DOM inteiro, inclusive partes escondidas
            for text in REMOVED_TEXTS:
                assert text not in html, f"'{text}' ainda está em #{view} ({width}px)"
        context.close()


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_overview_layout_in_both_themes(browser, base_url, scheme):
    context = browser.new_context(viewport={"width": 1366, "height": 768}, color_scheme=scheme)
    page = context.new_page()
    open_view(page, base_url, "visao-geral")
    page.wait_for_selector("#overview-kpis:not(.loading) .card")
    assert page.evaluate("document.documentElement.dataset.theme") == scheme
    boxes = [page.locator("#view-visao-geral .module").nth(i).bounding_box() for i in range(8)]
    # Em 1366 px a grade tem 4 colunas: duas linhas, cartões de mesma altura e topos alinhados.
    assert len({round(box["y"]) for box in boxes}) == 2
    for row in (boxes[:4], boxes[4:]):
        assert len({round(box["height"]) for box in row}) == 1
    kpis = [page.locator("#overview-kpis .card").nth(i).bounding_box() for i in range(5)]
    assert len({round(box["y"]) for box in kpis}) == 1
    page.click("#theme-toggle")
    assert page.evaluate("document.documentElement.dataset.theme") != scheme
    context.close()


# ---------------- Robustez de rede e estado ----------------

def test_newer_request_cancels_older_one(page, base_url):
    open_view(page, base_url, "visao-geral")
    outcome = page.evaluate("""async () => {
        const { api } = await import('/static/js/core.js');
        const older = api('/api/scan?n=3000&all_pairs=1&threshold_nm=20', { key: 'teste' }).then(() => 'ok', (e) => e.name);
        const newer = api('/api/health', { key: 'teste' });
        return [await older, (await newer).status];
    }""")
    assert outcome == ["AbortError", "ok"]


def test_radar_keeps_latest_state_under_slow_network_and_offline(page, base_url):
    if ENGINE != "chromium":
        pytest.skip("emulação de rede via CDP só existe no Chromium")
    open_view(page, base_url, "radar")
    page.wait_for_selector("#radar-cards .card")
    session = page.context.new_cdp_session(page)
    session.send("Network.enable")
    session.send("Network.emulateNetworkConditions",
                 {"offline": False, "latency": 600, "downloadThroughput": 200_000, "uploadThroughput": 200_000})
    for seed in ("31", "32", "33"):
        page.fill("#radar-seed", seed)
        page.wait_for_timeout(300)
    page.wait_for_function("document.querySelector('#radar-source-banner').textContent.includes('seed 33')", timeout=20000)
    page.wait_for_timeout(1500)  # nenhuma resposta antiga pode chegar depois e sobrescrever
    assert "seed 33" in page.inner_text("#radar-source-banner")
    session.send("Network.emulateNetworkConditions",
                 {"offline": True, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
    page.fill("#radar-seed", "34")
    page.wait_for_selector("#radar-error:not([hidden])")
    assert "seed 33" in page.inner_text("#radar-source-banner")


def test_radar_playback_stops_when_leaving_the_section(page, base_url):
    open_view(page, base_url, "radar")
    page.wait_for_selector("#radar-cards .card")
    page.select_option("#radar-speed", "400")
    page.click("#radar-play")
    page.wait_for_function("Number(document.querySelector('#radar-minutes').value) >= 1", timeout=15000)
    page.click(".nav a[data-view='teoria']")
    page.wait_for_selector("[data-view-panel='teoria']:not([hidden])")
    minute = page.input_value("#radar-minutes")
    page.wait_for_timeout(1500)
    assert page.input_value("#radar-minutes") == minute
    assert page.get_attribute("#radar-play", "aria-pressed") == "false"


def test_rapid_algorithm_switching_ends_consistent(page, base_url):
    open_view(page, base_url, "laboratorio")
    page.wait_for_selector("#lab-summary .card")
    for name in ("Quick Sort", "Quickselect", "Merge Sort", "Subarray de soma máxima"):
        page.click(f"#lab-algorithms button:has-text('{name}')")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("#lab-summary .badge.ok")
    assert page.locator("#lab-algorithms button[aria-pressed='true']").inner_text() == "Subarray de soma máxima"
    assert "soma" in page.inner_text("#lab-summary .card .value >> nth=0")
    assert page.locator("#lab-form button[type=submit]").is_enabled()


# ---------------- Cenários em JSON ----------------

def test_lab_scenario_round_trip_and_rejects_invalid_files(page, base_url, tmp_path):
    open_view(page, base_url, "laboratorio")
    page.wait_for_selector("#lab-summary .card")
    page.click("#lab-algorithms button:has-text('Quickselect')")
    page.wait_for_selector("#lab-summary .badge.ok")
    page.select_option("#lab-pivot", "mediana_medianas")
    page.fill("#lab-k", "5")
    page.click("#lab-form button[type=submit]")
    page.wait_for_selector("#lab-summary:has-text('5º menor')")
    expected = page.inner_text("#lab-summary .card .value >> nth=0")
    with page.expect_download() as download:
        page.click("#lab-scenario-json-export")
    exported = download.value.path()
    with open(exported, encoding="utf-8") as file:
        data = json.load(file)
    assert data["tipo"] == "radar-dc-cenario" and data["algoritmo"] == "quickselect" and data["parametros"]["k"] == 5

    page.click("#lab-algorithms button:has-text('Merge Sort')")
    page.wait_for_selector("#lab-algorithms button[aria-pressed='true']:has-text('Merge Sort')")
    page.set_input_files("#lab-scenario-json-file", exported)
    page.wait_for_selector("#lab-algorithms button[aria-pressed='true']:has-text('Quickselect')")
    page.wait_for_selector("#lab-summary:has-text('5º menor')")
    assert page.inner_text("#lab-summary .card .value >> nth=0") == expected
    assert page.input_value("#lab-pivot") == "mediana_medianas"

    bad = tmp_path / "ruim.json"
    bad.write_text(json.dumps({"tipo": "radar-dc-cenario", "versao": 1, "modulo": "laboratorio",
                               "algoritmo": "merge_sort", "valores": [1, 2.5]}), encoding="utf-8")
    page.set_input_files("#lab-scenario-json-file", str(bad))
    page.wait_for_selector("#lab-error:has-text('inteiros')")
    not_json = tmp_path / "texto.json"
    not_json.write_text("isto não é json", encoding="utf-8")
    page.set_input_files("#lab-scenario-json-file", str(not_json))
    page.wait_for_selector("#lab-error:has-text('JSON válido')")


def test_visualizer_scenario_round_trip(page, base_url, tmp_path):
    open_view(page, base_url, "visualizador")
    page.wait_for_selector("#viz-step-title:has-text('etapa')")
    result = page.inner_text("#viz-result")
    with page.expect_download() as download:
        page.click("#viz-scenario-json-export")
    exported = download.value.path()
    page.select_option("#viz-case", "dois_pontos")
    page.wait_for_selector("#viz-result:has-text('#0 – #1')")
    page.set_input_files("#viz-scenario-json-file", exported)
    page.wait_for_function("document.querySelector('#viz-mode').value === 'custom'")
    page.wait_for_function("(expected) => document.querySelector('#viz-result').innerText === expected", arg=result)
    wrong = tmp_path / "lab.json"
    wrong.write_text(json.dumps({"tipo": "radar-dc-cenario", "versao": 1, "modulo": "laboratorio"}), encoding="utf-8")
    page.set_input_files("#viz-scenario-json-file", str(wrong))
    page.wait_for_selector("#viz-error:has-text('não é do visualizador')")


# ---------------- Acessibilidade e segurança ----------------

CONTRAST_JS = """(selectors) => {
  const parse = (c) => (c.match(/[\\d.]+/g) || []).map(Number);
  const lum = ([r, g, b]) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const blend = (top, bottom) => {
    const a = top.length > 3 ? top[3] : 1;
    return [0, 1, 2].map((i) => top[i] * a + bottom[i] * (1 - a));
  };
  const background = (el) => {
    const layers = [];
    for (let node = el; node; node = node.parentElement) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c.length && (c.length < 4 || c[3] > 0)) layers.push(c);
      if (c.length && (c.length < 4 || c[3] === 1)) break;
    }
    let color = [255, 255, 255];
    for (const layer of layers.reverse()) color = blend(layer, color);
    return color;
  };
  const out = [];
  for (const selector of selectors) {
    for (const el of document.querySelectorAll(selector)) {
      if (!el.offsetParent || !el.textContent.trim()) continue;
      const bg = background(el);
      const fg = blend(parse(getComputedStyle(el).color), bg);
      const [a, b] = [lum(fg), lum(bg)];
      out.push([selector, (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)]);
      break;
    }
  }
  return out;
}"""
CONTRAST_SELECTORS = [
    ".nav a:not([aria-current])", ".nav a[aria-current]", ".view-head p", ".kicker", ".status-pill", ".card .label",
    ".card .hint", ".card.alerting .value", ".module-text", ".module-meta", ".dc-tag", "button.primary",
    "button:not(.primary)", "footer", ".banner", ".badge.ok", ".small.muted", "th", "td", "a",
]


@pytest.mark.parametrize("scheme", ["dark", "light"])
@pytest.mark.parametrize("view", ["visao-geral", "radar", "laboratorio", "benchmarks"])
def test_text_contrast_meets_wcag_aa(browser, base_url, scheme, view):
    context = browser.new_context(viewport={"width": 1366, "height": 900}, color_scheme=scheme)
    page = context.new_page()
    open_view(page, base_url, view)
    page.wait_for_load_state("networkidle")
    if view == "benchmarks":
        page.fill("#bench-sizes", "50, 100")
        page.click("#bench-form button[type=submit]")
        page.wait_for_selector("#bench-result tbody tr")
    ratios = page.evaluate(CONTRAST_JS, CONTRAST_SELECTORS)
    assert len(ratios) >= 8
    low = [(selector, round(ratio, 2)) for selector, ratio in ratios if ratio < 4.5]
    assert not low, f"contraste abaixo de 4,5:1 em {scheme}: {low}"
    context.close()


def test_reduced_motion_disables_animations(browser, base_url):
    context = browser.new_context(reduced_motion="reduce")
    page = context.new_page()
    open_view(page, base_url, "visao-geral")
    page.evaluate("document.getElementById('overview-kpis').classList.add('loading')")
    name = page.evaluate("getComputedStyle(document.getElementById('overview-kpis'), '::after').animationName")
    assert name == "none"
    context.close()


def test_overview_modules_are_keyboard_reachable_with_visible_focus(page, base_url):
    if ENGINE == "webkit":
        pytest.skip("o WebKit, como o Safari por padrão, não inclui links na ordem do Tab")
    open_view(page, base_url, "visao-geral")
    page.focus("#view-visao-geral .module[href='#radar']")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.getAttribute('href')") == "#visualizador"
    assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle") != "none"
    page.keyboard.press("Enter")
    page.wait_for_selector("[data-view-panel='visualizador']:not([hidden])")


def test_dynamic_text_is_never_parsed_as_html(page, base_url):
    payload = "<img src=x onerror=window.__xss=1>"

    def poisoned_scan(route):
        response = route.fetch()
        data = response.json()
        for plane in data["aircraft"]:
            plane["callsign"] = payload
        for band in data["bands"]:
            for plane in band["pair"]:
                plane["callsign"] = payload
        route.fulfill(response=response, json=data)

    page.route("**/api/scan**", poisoned_scan)
    open_view(page, base_url, "radar")
    page.wait_for_selector("#bands-table tbody tr")
    page.locator("#bands-table tbody tr").first.click()
    assert payload in page.inner_text("#bands-table")
    assert page.evaluate("window.__xss") is None
    assert page.locator("#view-radar img[src='x']").count() == 0
