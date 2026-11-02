"""Fixtures dos testes de interface com navegador real (Playwright).

Rode com:  pytest -m e2e
Requer `pip install -r requirements-dev.txt` e um navegador. Motor escolhido por
E2E_BROWSER (chromium, firefox ou webkit; padrão chromium). Para chromium, o canal
vem de E2E_BROWSER_CHANNEL (chrome, msedge) ou, sem ele, tenta o Chromium do
Playwright, depois Chrome e Edge instalados. Firefox/WebKit exigem
`python -m playwright install firefox webkit`.
"""
import os
import threading

import pytest
from werkzeug.serving import make_server

from app import app

try:
    from playwright import sync_api as playwright_api
except ImportError:  # Playwright é dependência só de desenvolvimento (requirements-dev.txt)
    playwright_api = None

VIEWS = ["visao-geral", "radar", "visualizador", "laboratorio", "comparacao", "benchmarks", "teoria", "exercicios", "ajuda"]


@pytest.fixture(scope="module")
def base_url():
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


ENGINE = os.environ.get("E2E_BROWSER", "chromium")


@pytest.fixture(scope="module")
def browser():
    if playwright_api is None:
        pytest.skip("Playwright não instalado: pip install -r requirements-dev.txt")
    channels = [os.environ["E2E_BROWSER_CHANNEL"]] if os.environ.get("E2E_BROWSER_CHANNEL") else [None, "chrome", "msedge"]
    if ENGINE != "chromium":
        channels = [None]
    with playwright_api.sync_playwright() as p:
        launcher = getattr(p, ENGINE)
        for channel in channels:
            try:
                instance = launcher.launch(channel=channel) if channel else launcher.launch()
                break
            except Exception:  # navegador ausente: tenta o próximo canal
                continue
        else:
            pytest.skip(f"navegador '{ENGINE}' indisponível para o Playwright")
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    page.on("console", lambda message: page.errors.append(message.text) if message.type == "error" else None)
    yield page
    context.close()


def open_view(page, base_url, view):
    page.goto(f"{base_url}#{view}")
    page.wait_for_selector(f"[data-view-panel='{view}']:not([hidden])")
