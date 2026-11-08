/* Local filtering only: the complete reference remains readable without JS. */
(function () {
    'use strict';
    function normalise(value) {
        return value.toLocaleLowerCase('ru').replace(/ё/g, 'е').replace(/[’‘]/g, "'").trim();
    }
    function initialise(root) {
        var parentLink = document.querySelector('.dc-breadcrumbs a:last-of-type');
        document.querySelectorAll('#mw-panel a').forEach(function (link) {
            var current = link.pathname === window.location.pathname;
            var section = parentLink && link.pathname === parentLink.pathname;
            link.classList.toggle('dc-nav-active', Boolean(current || section));
            if (current) link.setAttribute('aria-current', 'page');
        });
        var heading = document.getElementById('firstHeading');
        if (heading && document.querySelector('.mw-parser-output') && !document.querySelector('.dc-mobile-quicknav')) {
            var navigation = document.createElement('nav');
            navigation.className = 'dc-mobile-quicknav';
            navigation.setAttribute('aria-label', 'Разделы вики');
            [['Вики', 'Заглавная страница'], ['Карта', 'Ветви подземелья'],
             ['Предметы', 'Предметы'], ['Заклинания', 'Заклинания'], ['Существа', 'Существа']].forEach(function (item) {
                var link = document.createElement('a');
                link.textContent = item[0];
                link.href = '/wiki/' + encodeURIComponent(item[1].replace(/ /g, '_'));
                navigation.appendChild(link);
            });
            heading.parentNode.insertBefore(navigation, heading);
        }
        root.querySelectorAll('.dc-directory').forEach(function (directory) {
            if (directory.dataset.dcReady) return;
            directory.dataset.dcReady = '1';
            var tools = directory.querySelector('.dc-directory-tools');
            if (!tools) return;
            var entries = Array.from(directory.querySelectorAll('.dc-icon-entry'));
            var records = entries.map(function (entry) {
                return { element: entry, text: normalise(entry.dataset.dcSearch || entry.textContent) };
            });
            var label = document.createElement('label');
            label.className = 'dc-filter-label';
            label.appendChild(document.createTextNode('Найти в этом разделе'));
            var input = document.createElement('input');
            input.type = 'search';
            input.className = 'dc-directory-filter';
            input.placeholder = 'Русское или английское название';
            input.autocomplete = 'off';
            label.appendChild(input);
            var reset = document.createElement('button');
            reset.type = 'button';
            reset.className = 'dc-filter-reset';
            reset.textContent = 'Сбросить';
            var count = document.createElement('span');
            count.className = 'dc-filter-count';
            count.setAttribute('role', 'status');
            count.setAttribute('aria-live', 'polite');
            var empty = document.createElement('p');
            empty.className = 'dc-filter-empty';
            empty.textContent = 'Совпадений нет. Попробуйте часть русского или английского названия.';
            empty.hidden = true;
            tools.append(label, reset, count);
            directory.appendChild(empty);
            function filter() {
                var words = normalise(input.value).split(/\s+/).filter(Boolean);
                var visible = 0;
                records.forEach(function (record) {
                    var matches = words.every(function (word) { return record.text.includes(word); });
                    record.element.hidden = !matches;
                    if (matches) visible++;
                });
                directory.querySelectorAll('.dc-directory-section').forEach(function (section) {
                    section.hidden = !Array.from(section.querySelectorAll('.dc-icon-entry')).some(function (entry) { return !entry.hidden; });
                });
                count.textContent = 'Показано ' + visible + ' из ' + records.length;
                empty.hidden = visible !== 0;
                reset.disabled = input.value.length === 0;
            }
            input.addEventListener('input', filter);
            input.addEventListener('keydown', function (event) {
                if (event.key === 'Escape') { input.value = ''; filter(); }
            });
            reset.addEventListener('click', function () { input.value = ''; filter(); input.focus(); });
            var jumps = directory.previousElementSibling;
            if (jumps && jumps.classList.contains('dc-section-jumps')) {
                jumps.addEventListener('click', function (event) {
                    if (event.target.closest('a')) { input.value = ''; filter(); }
                });
            }
            filter();
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { initialise(document); });
    } else {
        initialise(document);
    }
    if (typeof mw !== 'undefined' && mw.hook) {
        mw.hook('wikipage.content').add(function ($content) { initialise($content[0]); });
    }
}());
