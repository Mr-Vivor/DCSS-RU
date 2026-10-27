"""Run a real WebTiles server and check the Russian browser interface."""
from pathlib import Path
import os
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "crawl-ref/source"
ARTIFACTS = ROOT / "web-smoke"


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    config = SOURCE / "webserver/config.yml"
    if config.exists():
        raise SystemExit("Smoke test requires a checkout without webserver/config.yml")
    config.write_text("dgl_mode: false\nbind_address: 127.0.0.1\nbind_port: 8080\nno_cache: true\n", encoding="utf8")
    server = None
    try:
        with (ARTIFACTS / "server.log").open("w", encoding="utf8") as log:
            server = subprocess.Popen(["python3", "webserver/server.py"], cwd=SOURCE,
                stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "LANG": "C.UTF-8"})
            deadline = time.monotonic() + 40
            while True:
                if server.poll() is not None:
                    raise RuntimeError("WebTiles server exited; inspect server.log")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8080/", timeout=2) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.25)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto("http://127.0.0.1:8080/")
                page.wait_for_function("document.body.innerText.includes('Введите имя')", timeout=60000)
                page.screenshot(path=str(ARTIFACTS / "russian-startup.png"), full_page=True)
                (ARTIFACTS / "startup.txt").write_text(page.locator("body").inner_text(), encoding="utf8")
                assert "Обучение" in page.locator("body").inner_text()
                # A long Cyrillic colour span and an unbreakable token must fit
                # in the compact pane, even at a narrow browser width.
                result = page.evaluate("""async () => {
                    // Game CSS is loaded by WebTiles itself. Reuse its rule.
                    const box = document.createElement('div');
                    box.style.cssText = 'width:240px;font:16px monospace';
                    const msg = document.createElement('div');
                    msg.className = 'game_message';
                    const span = document.createElement('span');
                    span.style.color = 'red';
                    const text = 'Длинная цветная подсказка: ' + 'передвижение'.repeat(30);
                    span.textContent = text;
                    msg.append(span); box.append(msg); document.body.append(box);
                    const result = {fits: msg.scrollWidth <= box.clientWidth,
                                    complete: msg.textContent === text,
                                    wraps: msg.clientHeight > 32};
                    box.remove(); return result;
                }""")
                assert result == {"fits": True, "complete": True, "wraps": True}, result
                assert not errors, errors
                browser.close()
                print("Russian startup renders; long Cyrillic messages wrap without horizontal clipping.")
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        config.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
