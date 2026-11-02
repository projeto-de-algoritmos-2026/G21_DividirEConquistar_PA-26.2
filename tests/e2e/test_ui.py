"""Testes de interface: fluxos de cada seção. Rode com  pytest -m e2e  (ver conftest.py)."""
import re

import pytest

from tests.e2e.conftest import ENGINE, VIEWS, open_view

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("width,height", [(1920, 1080), (1366, 768), (768, 1024), (390, 844)])
def test_every_view_loads_without_errors_or_horizontal_scroll(browser, base_url, width, height):
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    for view in VIEWS:
        open_view(page, base_url, view)
        page.wait_for_load_state("networkidle")
        assert page.locator(f".nav a[data-view='{view}']").get_attribute("aria-current") == "page"
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 0, f"{view} rola na horizontal em {width}px"
        text = page.inner_text(f"[data-view-panel='{view}']")
        assert not re.search(r"(null|undefined|NaN)", text), f"{view} mostra valor inválido"
    assert errors == []
    context.close()


def test_radar_cards_filters_and_selection(page, base_url):
    open_view(page, base_url, "radar")
    page.wait_for_selector("#radar-cards .card")
    expected = page.request.get(f"{base_url}api/scan?n=400&seed=21").json()["summary"]
    cards = page.locator("#radar-cards .card .value")
    assert cards.nth(0).inner_text() == "400"
    assert cards.nth(1).inner_text() == str(expected["bands_analyzed"])
    assert cards.nth(2).inner_text() == str(expected["bands_below_threshold"])

    rows = page.locator("#bands-table tbody tr")
    total = rows.count()
    page.check("#filter-alert")
    assert rows.count() == expected["bands_below_threshold"]
    page.uncheck("#filter-alert")
    assert rows.count() == total

    rows.first.click()
    assert rows.first.get_attribute("aria-selected") == "true"
    assert page.locator("#band-detail").is_visible()
    assert "Par mínimo" in page.locator("#band-detail").inner_text()

    page.fill("#filter-search", "ZZZ-NAO-EXISTE")
    assert "Nenhuma faixa" in page.locator("#bands-table").inner_text()
    assert page.errors == []


def test_radar_parameters_validation_and_url(page, base_url):
    open_view(page, base_url, "radar")
    page.wait_for_selector("#radar-cards .card")
    with page.expect_response(re.compile(r"/api/scan\?.*n=120")):
        page.fill("#radar-n", "120")
    page.wait_for_function("document.querySelector('#radar-cards .card .value').textContent === '120'")
    assert "n=120" in page.url

    page.fill("#radar-n", "99999")
    page.wait_for_selector("#radar-error:not([hidden])")
    assert "Aeronaves" in page.inner_text("#radar-error")
    assert page.get_attribute("#radar-n", "aria-invalid") == "true"

    page.select_option("#radar-preset", "snapshot")
    page.wait_for_function("document.querySelector('#radar-source-banner').textContent.includes('Snapshot histórico')")
    assert page.locator("#radar-n").is_hidden()
    banner = page.inner_text("#radar-source-banner")
    assert "capturado em" in banner and "captura única" in banner


def test_radar_playback_advances_and_pauses(page, base_url):
    open_view(page, base_url, "radar")
    page.wait_for_selector("#radar-cards .card")
    page.select_option("#radar-speed", "400")
    page.click("#radar-play")
    page.wait_for_function("Number(document.querySelector('#radar-minutes').value) >= 2", timeout=15000)
    page.click("#radar-play")
    stopped = page.input_value("#radar-minutes")
    page.wait_for_timeout(1200)
    assert page.input_value("#radar-minutes") == stopped
    page.click("#radar-restart")
    page.wait_for_function("document.querySelector('#radar-minutes').value === '0'")


def test_radar_reports_network_errors(page, base_url):
    open_view(page, base_url, "radar")
    page.wait_for_selector("#radar-cards .card")
    page.route("**/api/scan**", lambda route: route.abort())
    page.fill("#radar-seed", "5")
    page.wait_for_selector("#radar-error:not([hidden])")
    assert "Falha de rede" in page.inner_text("#radar-error")


def test_radar_survives_leaflet_failure(browser, base_url):
    context = browser.new_context()
    context.route("**/unpkg.com/**", lambda route: route.abort())
    page = context.new_page()
    page.goto(f"{base_url}#radar")
    page.wait_for_selector("#radar-cards .card")
    assert "não carregou" in page.inner_text("#map")
    assert page.locator("#bands-table tbody tr").count() > 0
    context.close()


def test_visualizer_navigation_and_keyboard(page, base_url):
    open_view(page, base_url, "visualizador")
    page.wait_for_function("document.querySelector('#viz-step-title').textContent.includes('etapa 1 de')")
    total = int(re.search(r"de (\d+)", page.inner_text("#viz-step-title")).group(1))
    page.focus("#viz-stage")
    page.keyboard.press("End")
    assert f"etapa {total} de {total}" in page.inner_text("#viz-step-title")
    assert page.locator("#viz-pseudo li[aria-current='true']").inner_text().strip().startswith("para cada")
    page.keyboard.press("ArrowLeft")
    assert f"etapa {total - 1} de {total}" in page.inner_text("#viz-step-title")
    page.keyboard.press("Home")
    assert "etapa 1 de" in page.inner_text("#viz-step-title")
    assert "confere com a força bruta" in page.inner_text("#viz-result")
    assert "null" not in page.inner_text("#viz-result")
    assert page.locator("#viz-tree circle").count() > 1
    assert page.errors == []


def test_visualizer_custom_points_and_radar_band(page, base_url):
    open_view(page, base_url, "visualizador")
    page.wait_for_selector("#viz-step-title:has-text('etapa')")
    page.select_option("#viz-mode", "custom")
    page.fill("#viz-points", "0, 0\nabc")
    page.click("#viz-form button[type=submit]")
    page.wait_for_selector("#viz-error:not([hidden])")
    page.fill("#viz-points", "0, 0\n3, 4\n10, 10\n10, 10.5")
    page.click("#viz-form button[type=submit]")
    page.wait_for_function("document.querySelector('#viz-result').textContent.includes('0,50')")

    page.goto(f"{base_url}#visualizador?band=370")
    page.wait_for_function("document.querySelector('#viz-step-title').textContent.includes('FL370')")
    assert page.input_value("#viz-band") == "370"


@pytest.mark.parametrize("name", ["Merge Sort", "Quick Sort", "Quickselect", "Contagem de inversões", "Subarray de soma máxima"])
def test_lab_runs_each_algorithm(page, base_url, name):
    open_view(page, base_url, "laboratorio")
    page.wait_for_selector("#lab-summary .card")
    with page.expect_response("**/api/lab/run"):
        page.click(f"#lab-algorithms button:has-text('{name}')")
    page.wait_for_selector("#lab-summary .badge.ok")
    assert page.locator(f"#lab-algorithms button:has-text('{name}')").get_attribute("aria-pressed") == "true"
    assert page.locator("#lab-svg rect").count() > 1
    page.focus("#lab-stage")
    page.keyboard.press("End")
    assert page.locator("#lab-pseudo li[aria-current='true']").count() == 1
    # A última etapa do Quickselect mostra só o grupo final, que pode ter 1 elemento.
    assert page.locator("#lab-svg rect").count() >= 1
    assert page.errors == []


def test_lab_validation_and_large_input(page, base_url):
    open_view(page, base_url, "laboratorio")
    page.wait_for_selector("#lab-summary .card")
    page.click("#lab-algorithms button:has-text('Quickselect')")
    page.wait_for_selector("#lab-summary .badge.ok")
    page.fill("#lab-k", "999")
    page.click("#lab-form button[type=submit]")
    page.wait_for_selector("#lab-error:not([hidden])")
    page.fill("#lab-k", "3")
    page.fill("#lab-n", "500")
    page.click("#lab-form button[type=submit]")
    page.wait_for_selector("#lab-summary:has-text('passo a passo fica desligado')")
    page.select_option("#lab-mode", "custom")
    page.fill("#lab-values", "3, x, 1")
    page.click("#lab-form button[type=submit]")
    page.wait_for_selector("#lab-error:has-text('inteiros')")


def test_compare_table(page, base_url):
    open_view(page, base_url, "comparacao")
    page.fill("#compare-n", "120")
    page.fill("#compare-repeats", "1")
    page.click("#compare-form button[type=submit]")
    page.wait_for_selector("#compare-result tbody tr >> nth=5")
    assert page.locator("#compare-result .badge.ok").count() == 6
    header = page.locator("#compare-result th button:has-text('Razão')")
    header.click()
    assert page.locator("#compare-result th[aria-sort='ascending']").count() == 1


def test_benchmark_chart_table_and_export(page, base_url):
    open_view(page, base_url, "benchmarks")
    page.wait_for_selector("#bench-algorithm option", state="attached")
    page.select_option("#bench-algorithm", "quick_sort")
    assert page.locator(".bench-pivot").is_visible()
    page.fill("#bench-sizes", "50, 200")
    page.fill("#bench-repeats", "2")
    page.click("#bench-form button[type=submit]")
    page.wait_for_selector("#bench-result tbody tr >> nth=1")
    assert page.locator("#bench-result .chart circle").count() >= 4
    with page.expect_download() as download:
        page.click("text=Exportar CSV")
    path = download.value.path()
    with open(path, encoding="utf-8") as file:
        lines = file.read().strip().splitlines()
    assert lines[0].startswith("algorithm,scenario,seed,n,") and len(lines) == 3
    page.fill("#bench-sizes", "abc")
    page.click("#bench-form button[type=submit]")
    page.wait_for_selector("#bench-error:not([hidden])")


def test_exercise_check_flow(page, base_url):
    open_view(page, base_url, "exercicios")
    page.wait_for_selector("#ex-answer")
    expected = page.request.post(f"{base_url}api/exercises/check",
                                 data={"type": "inversoes", "seed": 1, "answer": -1}).json()["expected"]
    page.fill("#ex-answer", "-1")
    page.click("#ex-answer-form button[type=submit]")
    page.wait_for_selector("#ex-feedback .banner.error")
    page.fill("#ex-answer", str(expected))
    page.click("#ex-answer-form button[type=submit]")
    page.wait_for_selector("#ex-feedback .banner.ok")
    page.select_option("#ex-type", "teorema_mestre")
    page.wait_for_selector("input[name=ex-option]")


def test_theme_toggle_and_theory(page, base_url):
    open_view(page, base_url, "teoria")
    page.wait_for_selector("#theory-content h3")
    before = page.evaluate("document.documentElement.dataset.theme")
    page.click("#theme-toggle")
    assert page.evaluate("document.documentElement.dataset.theme") != before
    page.click("#theory-nav button:has-text('Quickselect')")
    assert "Quickselect" in page.inner_text("#theory-content h3")
    assert "mediana das medianas" in page.inner_text("#theory-content").lower()
    assert page.locator("#theory-content .pseudo li").count() == 7


def test_keyboard_navigation_reaches_nav_with_visible_focus(page, base_url):
    if ENGINE == "webkit":
        pytest.skip("o WebKit, como o Safari por padrão, não inclui links na ordem do Tab")
    open_view(page, base_url, "visao-geral")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip-link"
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    focused = page.evaluate("document.activeElement.getAttribute('href')")
    assert focused == "#visao-geral"
    outline = page.evaluate("getComputedStyle(document.activeElement).outlineStyle")
    assert outline != "none"
