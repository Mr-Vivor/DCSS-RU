"""Run a real WebTiles server and check the Russian browser interface."""
from pathlib import Path
import os
import subprocess
import shutil
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
                # Hosted runners already include Chrome. Reuse it instead of
                # reinstalling Chromium and unrelated font packages each push.
                browser = playwright.chromium.launch(
                    channel="chrome" if shutil.which("google-chrome") else None)
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                page.goto("http://127.0.0.1:8080/")
                try:
                    page.wait_for_function("document.body.innerText.includes('Введите имя')", timeout=60000)
                except Exception:
                    page.screenshot(path=str(ARTIFACTS / "startup-failure.png"), full_page=True)
                    (ARTIFACTS / "startup-failure.txt").write_text(
                        page.locator("body").inner_text() + "\n" + "\n".join(errors), encoding="utf8")
                    raise
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
                # Going directly to a named character skips the main menu and
                # missed the reported black screen after character creation.
                try:
                    page.keyboard.type("RuWebSmoke", delay=30)
                    page.keyboard.press("Enter")
                    page.get_by_text("j - Человек", exact=True).click()
                    page.get_by_text("a - Воин", exact=True).click()
                    page.get_by_text("a - рапира", exact=True).wait_for(state="visible")
                    # Reproduce the stale-process/error dialog left above a
                    # hidden lobby. The game can advance by keyboard while its
                    # full-screen overlay still intercepts pointer input.
                    page.evaluate("""() => new Promise(resolve => {
                        require(['client'], client => {
                            client.show_dialog('#stale_processes_message');
                            resolve();
                        });
                    })""")
                    assert page.locator("#overlay").is_visible()
                    page.keyboard.press("a")
                    page.wait_for_function("""() => {
                        const hp = document.querySelector('#stats_hp');
                        const normal = document.querySelector('#normal');
                        return hp && Number(hp.textContent) > 0
                            && normal && getComputedStyle(normal).display !== 'none'
                            && getComputedStyle(document.querySelector('#overlay')).display === 'none'
                            && document.querySelectorAll('#ui-stack > .ui-popup').length === 0;
                    }""", timeout=60000)
                    pixels = page.locator("#dungeon").evaluate("""canvas => {
                        const bounds = canvas.getBoundingClientRect();
                        const pixels = canvas.getContext('2d').getImageData(
                            0, 0, canvas.width, canvas.height).data;
                        let coloured = 0;
                        for (let i = 0; i < pixels.length; i += 4)
                            if (pixels[i] + pixels[i + 1] + pixels[i + 2] > 60)
                                ++coloured;
                        return {width: bounds.width, height: bounds.height, coloured};
                    }""")
                    assert pixels["width"] > 100 and pixels["height"] > 100, pixels
                    assert pixels["coloured"] > 200, pixels
                    body = page.locator("body").inner_text()
                    assert "Добро пожаловать, RuWebSmoke. Человек · Воин." in body, body
                    assert "Сфер" in body, body
                    assert "Orb of Zot" not in body, body
                    assert "Welcome" not in body, body
                    page.screenshot(path=str(ARTIFACTS / "first-level.png"), full_page=True)
                    (ARTIFACTS / "first-level.txt").write_text(page.locator("body").inner_text(), encoding="utf8")
                except Exception:
                    page.screenshot(path=str(ARTIFACTS / "newgame-failure.png"), full_page=True)
                    (ARTIFACTS / "newgame-failure.txt").write_text(
                        page.locator("body").inner_text() + "\n" + "\n".join(errors), encoding="utf8")
                    raise
                assert not errors, errors
                browser.close()
                print("Russian startup and first level render; character creation reaches a visible dungeon without reloading; Cyrillic messages wrap.")
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
