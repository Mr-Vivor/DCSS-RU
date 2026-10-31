"""Run a real WebTiles server and check the Russian browser interface."""
from pathlib import Path
import os
import re
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
                    assert "+0 рапира" in body, body
                    assert "+0 rapier" not in body, body
                    # Spectators may receive an old menu scroll after a popup
                    # closes. Exercise the real protocol handler with no menu.
                    page.evaluate("""() => new Promise(resolve => {
                        require(['comm'], comm => {
                            comm.handle_message({msg:'menu_scroll', first:0, force:true});
                            resolve();
                        });
                    })""")
                    page.screenshot(path=str(ARTIFACTS / "first-level.png"), full_page=True)
                    (ARTIFACTS / "first-level.txt").write_text(page.locator("body").inner_text(), encoding="utf8")
                    # Help is assembled from descriptions plus configurable
                    # bindings. Exercise the actual popup after substitution.
                    page.keyboard.type("?")
                    page.wait_for_function("document.body.innerText.includes('Содержание руководства')")
                    page.keyboard.type("?")
                    page.wait_for_function("document.body.innerText.includes('Передвижение:')")
                    help_text = page.locator("body").inner_text()
                    assert "зелья (выпить — q)" in help_text, help_text
                    assert "hand weapons" not in help_text, help_text
                    assert "uaff" not in help_text, help_text
                    page.screenshot(path=str(ARTIFACTS / "russian-keyhelp.png"), full_page=True)
                    (ARTIFACTS / "keyhelp.txt").write_text(help_text, encoding="utf8")
                    page.keyboard.press("Escape")
                    page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    page.keyboard.press("Control+x")
                    page.wait_for_function("document.body.innerText.includes('В поле зрения:')")
                    visible_menu = page.locator("#ui-stack > .ui-popup").last
                    assert "наведение/переход" in visible_menu.inner_text(), visible_menu.inner_text()
                    assert "select to" not in visible_menu.inner_text(), visible_menu.inner_text()
                    page.screenshot(path=str(ARTIFACTS / "visible-objects.png"), full_page=True)
                    page.keyboard.type("!")
                    page.wait_for_function("document.body.innerText.includes('выбор — описание')")
                    page.screenshot(path=str(ARTIFACTS / "visible-objects-examine.png"), full_page=True)
                    page.keyboard.press("Escape")
                    page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    # Navigation menus and waypoint edits cost no turns. Keep
                    # their real letter/number bindings while checking Russian
                    # labels through the same path as normal player input.
                    page.keyboard.press("Control+w")
                    page.wait_for_function("document.body.innerText.includes('Какой номер назначить путевой точке?')")
                    page.keyboard.type("0")
                    page.wait_for_function("document.body.innerText.includes('Путевой точке 0 назначено место:')")
                    page.keyboard.type("G")
                    page.wait_for_function("document.body.innerText.includes('Куда идти?') && document.body.innerText.includes('* — список путевых точек')")
                    page.screenshot(path=str(ARTIFACTS / "travel-menu.png"), full_page=True)
                    page.keyboard.type("*")
                    page.wait_for_function("document.body.innerText.includes('* — список ветвей')")
                    page.screenshot(path=str(ARTIFACTS / "waypoint-menu.png"), full_page=True)
                    page.keyboard.type("*")
                    page.wait_for_function("document.body.innerText.includes('* — список путевых точек')")
                    page.keyboard.type("D")
                    page.wait_for_function("document.body.innerText.includes('На какой этаж ветви')")
                    page.screenshot(path=str(ARTIFACTS / "travel-depth-prompt.png"), full_page=True)
                    page.keyboard.press("Escape")
                    page.locator("#messages .game_message input").wait_for(state="detached")
                    page.keyboard.press("Control+w")
                    page.wait_for_function("""() => {
                        const messages = document.querySelectorAll('#messages .game_message');
                        return messages.length && messages[messages.length - 1].innerText
                            .includes('Какой номер назначить путевой точке?');
                    }""")
                    page.keyboard.type("D")
                    page.wait_for_function("document.body.innerText.includes('Какую путевую точку удалить?')")
                    page.keyboard.type("0")
                    page.wait_for_function("document.body.innerText.includes('Все путевые точки удалены.')")
                    (ARTIFACTS / "waypoint-result.txt").write_text(page.locator("body").inner_text(), encoding="utf8")
                    page.keyboard.press("Control+o")
                    page.wait_for_function("document.body.innerText.includes('Обзор подземелья и пометки этажей')")
                    overview_text = page.locator("#ui-stack > .ui-popup").last.inner_text()
                    assert "сведения о ветвях" in overview_text and "сведения о богах" in overview_text, overview_text
                    assert "press" not in overview_text, overview_text
                    assert re.search(r"Подземелье\s+\(1/\d+\)", overview_text), overview_text
                    assert "Dungeon" not in overview_text, overview_text
                    page.screenshot(path=str(ARTIFACTS / "dungeon-overview.png"), full_page=True)
                    (ARTIFACTS / "dungeon-overview.txt").write_text(page.locator("body").inner_text(), encoding="utf8")
                    page.keyboard.press("Escape")
                    page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    for query in ("рапира", "rapier"):
                        page.keyboard.press("Control+f")
                        search_input = page.locator("#messages .game_message input")
                        search_input.wait_for(state="visible")
                        search_input.fill(query)
                        page.keyboard.press("Enter")
                        page.wait_for_function("document.body.innerText.includes('режим:') && document.body.innerText.includes('сортировка:')")
                        search_menu = page.locator("#ui-stack > .ui-popup").last
                        search_text = search_menu.inner_text()
                        assert "Найдено:" in search_text and "+0 рапира" in search_text, search_text
                        assert "useless" not in search_text and "duplicates" not in search_text, search_text
                        if query == "рапира":
                            page.keyboard.type("!")
                            page.wait_for_function("document.body.innerText.includes('режим: осмотр')")
                            page.keyboard.type("/")
                            page.wait_for_function("document.body.innerText.includes('сортировка: расстояние') || document.body.innerText.includes('сортировка: название')")
                            page.keyboard.type("=")
                            page.wait_for_function("document.body.innerText.includes('показывать непригодное и повторы')")
                            page.screenshot(path=str(ARTIFACTS / "stash-search-ru.png"), full_page=True)
                            (ARTIFACTS / "stash-search-ru.txt").write_text(search_menu.inner_text(), encoding="utf8")
                        page.keyboard.press("Escape")
                        page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                except Exception:
                    page.screenshot(path=str(ARTIFACTS / "newgame-failure.png"), full_page=True)
                    (ARTIFACTS / "newgame-failure.txt").write_text(
                        page.locator("body").inner_text() + "\n" + "\n".join(errors), encoding="utf8")
                    raise
                # DGL-less mode has one shared process lock. Disconnect and wait
                # for its normal save/exit before starting the second character.
                page.context.close()
                deadline = time.monotonic() + 20
                while list(SOURCE.glob("game:*.ttyrec")):
                    if time.monotonic() >= deadline:
                        raise RuntimeError("First smoke character did not release its process lock")
                    time.sleep(0.1)
                # The Conjurer starts with Magic Dart learned and Searing Ray
                # in the library; its spell descriptions can be read at level 1.
                spell_context = browser.new_context(viewport={"width": 1280, "height": 900})
                spell_page = spell_context.new_page()
                spell_page.on("pageerror", lambda error: errors.append(str(error)))
                try:
                    spell_page.goto("http://127.0.0.1:8080/")
                    spell_page.wait_for_function("document.body.innerText.includes('Введите имя')", timeout=60000)
                    spell_page.keyboard.type("RuSpellSmoke", delay=30)
                    spell_page.keyboard.press("Enter")
                    spell_page.get_by_text("j - Человек", exact=True).click()
                    spell_page.get_by_text(re.compile(r"^[a-zA-Z] - Разрушитель$")).click()
                    spell_page.wait_for_function("""() => Number(document.querySelector('#stats_hp')?.textContent) > 0
                        && document.querySelectorAll('#ui-stack > .ui-popup').length === 0""", timeout=60000)
                    spell_page.keyboard.type("I")
                    spell_page.wait_for_function("document.body.innerText.includes('Выберите заклинание для просмотра описания')")
                    spell_page.screenshot(path=str(ARTIFACTS / "spell-menu.png"), full_page=True)
                    spell_page.keyboard.press("Escape")
                    spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    spell_page.keyboard.type("M")
                    spell_page.wait_for_function("document.body.innerText.includes('Заклинания (выучить)')")
                    spell_page.keyboard.press("Tab")
                    spell_page.wait_for_function("document.body.innerText.includes('Заклинания (описание)')")
                    spell_page.locator("#ui-stack li.selectable").filter(has_text="Обжигающий луч").click()
                    spell_page.wait_for_function("document.body.innerText.includes('непрерывный') && document.body.innerText.includes('сосредоточение')")
                    spell_page.screenshot(path=str(ARTIFACTS / "spell-description.png"), full_page=True)
                    assert "piercing ray" not in spell_page.locator("body").inner_text()
                    body = spell_page.locator("body").inner_text()
                    for expected in ("Точность:", "Защита:", "Сопротивления:", "недостаточно опыта"):
                        assert expected in body, body
                    for untranslated in ("Accuracy:", "Defences:", "Resists:", "experienced enough"):
                        assert untranslated not in body, body
                    spell_page.keyboard.press("Escape")
                    spell_page.wait_for_function("document.body.innerText.includes('Заклинания (описание)')")
                    spell_page.keyboard.press("Escape")
                    spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    spell_page.keyboard.type("Q")
                    spell_page.wait_for_function("document.body.innerText.includes('Какое действие подготовить?')")
                    spell_page.wait_for_function("document.body.innerText.includes('один раздел:')")
                    body = spell_page.locator("body").inner_text()
                    assert "все заклинания" in body, body
                    assert "focus mode" not in body, body
                    assert "Сотворить: Магический дротик" in body, body
                    assert "Cast:" not in body and "Magic Dart" not in body, body
                    spell_page.screenshot(path=str(ARTIFACTS / "quiver-menu.png"), full_page=True)
                    spell_page.keyboard.press("Escape")
                    spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    # This isolated CI character can create a fixed artefact.
                    # Check the same formatted description and inventory label
                    # that a player sees, without touching any public saves.
                    spell_page.keyboard.type("&")
                    spell_page.wait_for_function("document.body.innerText.includes('отладочный режим') || document.body.innerText.includes('Команда отладчика')")
                    if "Команда отладчика" not in spell_page.locator("body").inner_text():
                        spell_page.wait_for_function("document.body.innerText.includes('Для подтверждения введите')")
                        confirmation = spell_page.locator("body").inner_text()
                        assert 'Для подтверждения введите "wiz".' in confirmation, confirmation
                        assert "Confirm with" not in confirmation, confirmation
                        spell_page.keyboard.type("wiz")
                        spell_page.keyboard.press("Enter")
                        spell_page.wait_for_function("document.body.innerText.includes('Команда отладчика')")
                    spell_page.keyboard.type("%")
                    spell_page.wait_for_function("document.body.innerText.includes('Введите имя предмета')")
                    spell_page.keyboard.type("Wrath of Trog", delay=20)
                    spell_page.keyboard.press("Enter")
                    spell_page.wait_for_timeout(200)
                    spell_page.keyboard.type("g")
                    spell_page.wait_for_timeout(200)
                    spell_page.keyboard.type("i")
                    artefact_row = spell_page.locator("#ui-stack li.selectable").filter(has_text="Гнев Трога")
                    artefact_row.wait_for()
                    artefact_row.click()
                    spell_page.wait_for_function("document.body.innerText.includes('Яростный раскол') && document.body.innerText.includes('истощение сил')")
                    body = spell_page.locator("body").inner_text()
                    assert "RageSunder" not in body and "consecutive attacks" not in body, body
                    assert "when equipped" not in body, body
                    assert "+0 мантия (надето)" in body and "(worn)" not in body, body
                    for expected in ("Основа", "(Сил)", "(Навыки)", "(Чары)", "Тип оружия:", "Двуручное оружие", "(w) взять в руки", "(d) бросить", "(i) пометить"):
                        assert expected in body, body
                    for untranslated in ("falls into the", "handed weapon", "(Base ", "(Str)", "(Skill)", "(Ench)", ")ield", ")rop", ")nscribe"):
                        assert untranslated not in body, body
                    spell_page.screenshot(path=str(ARTIFACTS / "artefact-description.png"), full_page=True)
                    (ARTIFACTS / "artefact-description.txt").write_text(body, encoding="utf8")
                    # The final command must remain its own clickable hotkey,
                    # rather than being joined to the preceding translated verb.
                    spell_page.locator(".describe-item .actions [data-hotkey='i']").click()
                    spell_page.wait_for_function("document.body.innerText.includes('Какую пометку')")
                    spell_page.keyboard.press("Escape")
                    spell_page.locator("#messages .game_message input").wait_for(state="detached")
                    spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    # Add a fixed new spell to this isolated wizard character.
                    # No turn is spent and no production save is involved.
                    spell_page.keyboard.type("&!")
                    spell_page.locator("#messages .game_message input").wait_for(state="visible")
                    spell_page.locator("#messages .game_message input").fill("Manifold Assault")
                    spell_page.keyboard.press("Enter")
                    spell_page.locator("#messages .game_message input").wait_for(state="detached")
                    spell_page.wait_for_function("""() => {
                        const text = document.body.innerText;
                        return /Memorise|Выучить|Запомнить/.test(text)
                            && /consuming|Затраты/.test(text);
                    }""")
                    spell_page.keyboard.type("Y")
                    spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    spell_page.wait_for_function("document.body.innerText.includes('Заклинанию назначена клавиша')")
                    spell_page.keyboard.type("I")
                    spell_row = spell_page.locator("#ui-stack li.selectable").filter(has_text="Множественная атака")
                    spell_row.wait_for()
                    spell_row.click()
                    spell_page.wait_for_function("document.body.innerText.includes('вдвое меньше целей')")
                    expansion_text = spell_page.locator("#ui-stack > .ui-popup").last.inner_text()
                    assert "никогда не промахиваются" in expansion_text, expansion_text
                    assert "коллектор" not in expansion_text and "Warps space" not in expansion_text, expansion_text
                    assert "развитие «Перемещения»" in expansion_text and "Для этого потребуется" in expansion_text, expansion_text
                    assert "With your current stats" not in expansion_text and "XLs" not in expansion_text, expansion_text
                    spell_page.screenshot(path=str(ARTIFACTS / "manifold-description.png"), full_page=True)
                    (ARTIFACTS / "manifold-description.txt").write_text(expansion_text, encoding="utf8")
                    spell_page.keyboard.press("Escape")
                    spell_row.wait_for(state="visible")
                    spell_page.keyboard.press("Escape")
                    spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    # Replace only this isolated wizard's current tile. Inspect
                    # actual feature popups, including a resolved DB reference
                    # and an instruction with the configured stair key.
                    for feature, expected, absent in (
                        ("closed_door", ("Закрытая дверь", "чтобы открыть", "пользоваться снаряжением"), ("While adjacent", "wooden door")),
                        ("trap_dispersal_inactive", ("перезаряжается", "в поле зрения", "нескольких ходов"), ("[[A dispersal trap]]", "Anyone stepping")),
                        ("stone_stairs_down_i", ("Каменная лестница вниз", "каменная лестница", "клавишей", "Вы находитесь здесь", "спуститься"), ("While standing", "You are here", "the stone staircase", "go down")),
                    ):
                        spell_page.keyboard.type("&(")
                        feature_input = spell_page.locator("#messages .game_message input")
                        feature_input.wait_for(state="visible")
                        feature_input.fill(feature)
                        spell_page.keyboard.press("Enter")
                        feature_input.wait_for(state="detached")
                        spell_page.keyboard.type("xrv", delay=80)
                        popup = spell_page.locator("#ui-stack > .ui-popup").last
                        popup.wait_for(state="visible")
                        feature_text = popup.inner_text()
                        for text in expected:
                            assert text in feature_text, feature_text
                        for text in absent:
                            assert text not in feature_text, feature_text
                        look_text = spell_page.locator("#messages .game_message").last.inner_text()
                        assert re.search(r"[А-Яа-яЁё]", look_text), look_text
                        assert not re.search(r"A (closed door|dispersal trap|stone staircase)", look_text), look_text
                        spell_page.screenshot(path=str(ARTIFACTS / (feature + "-description.png")), full_page=True)
                        (ARTIFACTS / (feature + "-description.txt")).write_text(feature_text, encoding="utf8")
                        spell_page.keyboard.press("Escape")
                        spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                        spell_page.keyboard.press("Escape")
                    # Training targets: the generic WebTiles input must receive
                    # a translated prompt, preserve decimals and reject >27.
                    spell_page.keyboard.type("m")
                    spell_page.locator("#ui-stack > .ui-popup").last.wait_for(state="visible")
                    spell_page.keyboard.type("=a", delay=100)
                    skill_input = spell_page.locator("#input_dialog input")
                    skill_input.wait_for(state="visible")
                    prompt = spell_page.locator("#input_dialog").inner_text()
                    assert "Целевой" in prompt and "навыка" in prompt, prompt
                    assert "Enter a" not in prompt, prompt
                    spell_page.screenshot(path=str(ARTIFACTS / "skill-target-prompt.png"), full_page=True)
                    skill_input.fill("28")
                    spell_page.keyboard.press("Enter")
                    skill_input.wait_for(state="hidden")
                    spell_page.wait_for_function("document.body.innerText.includes('Целевой уровень навыка не может превышать 27')")
                    spell_page.screenshot(path=str(ARTIFACTS / "skill-target-limit.png"), full_page=True)
                    spell_page.keyboard.type("=a", delay=100)
                    skill_input.wait_for(state="visible")
                    skill_input.fill("6.5")
                    spell_page.keyboard.press("Enter")
                    skill_input.wait_for(state="hidden")
                    spell_page.keyboard.type("=a", delay=100)
                    skill_input.wait_for(state="visible")
                    assert skill_input.input_value() == "6.5", skill_input.input_value()
                    spell_page.keyboard.press("Escape")
                    skill_input.wait_for(state="hidden")
                    spell_page.keyboard.press("Escape")
                    spell_page.wait_for_function("document.querySelectorAll('#ui-stack > .ui-popup').length === 0")
                    # Only the isolated wizard joins a god and receives piety;
                    # inspect an ability even when current MP cannot pay for it.
                    for command, value in (("&_", "Okawaru"), ("&^", "160")):
                        spell_page.keyboard.type(command)
                        god_input = spell_page.locator("#messages .game_message input")
                        god_input.wait_for(state="visible")
                        god_input.fill(value)
                        spell_page.keyboard.press("Enter")
                        god_input.wait_for(state="detached")
                    spell_page.keyboard.type("a")
                    finesse_row = spell_page.locator("#ui-stack li.selectable").filter(has_text="Искусность")
                    finesse_row.wait_for()
                    spell_page.keyboard.type("!")
                    spell_page.wait_for_function("document.body.innerText.includes('Какую способность описать?')")
                    finesse_row.click()
                    spell_page.wait_for_function("document.body.innerText.includes('Затраты способности:')")
                    ability_text = spell_page.locator("#ui-stack > .ui-popup").last.inner_text()
                    for text in ("Искусность", "Магия: 5", "Благочестие:", "от максимально возможного благочестия"):
                        assert text in ability_text, ability_text
                    for text in ("This ability costs", "MP     :", "Piety  :", "Range:"):
                        assert text not in ability_text, ability_text
                    spell_page.screenshot(path=str(ARTIFACTS / "finesse-costs.png"), full_page=True)
                    (ARTIFACTS / "finesse-costs.txt").write_text(ability_text, encoding="utf8")
                except Exception:
                    spell_page.screenshot(path=str(ARTIFACTS / "spell-failure.png"), full_page=True)
                    (ARTIFACTS / "spell-failure.txt").write_text(spell_page.locator("body").inner_text(), encoding="utf8")
                    raise
                finally:
                    spell_context.close()
                assert not errors, errors
                browser.close()
                print("Russian startup, first level and key help render; character creation reaches a visible dungeon without reloading; Cyrillic messages wrap.")
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
