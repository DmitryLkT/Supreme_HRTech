/* Подборщик цветов. Включить: добавьте ?tune к адресу любой страницы. Выключить: ?tune=off.
   Цвета меняются на лету и запоминаются в браузере. «Копировать CSS» даёт готовый блок :root. */
(function () {
    var KEY = 'altra-tune', ON = 'altra-tune-on';
    var root = document.documentElement;
    var VARS = [
        ['--bg', 'Фон страницы'], ['--surface', 'Панели и карточки'], ['--ink', 'Основной текст'],
        ['--ink-soft', 'Вторичный текст'], ['--accent', 'Акцент'], ['--accent-soft', 'Фон акцента'],
        ['--accent-ink', 'Текст на акценте'], ['--line', 'Линии и рамки'], ['--alert', 'Ошибки'],
        ['--login-bg', 'Окно входа'], ['--login-line', 'Рамка окна входа'], ['--input-bg', 'Поля ввода']
    ];
    var q = location.search.match(/[?&]tune(?:=(\w+))?/);
    try {
        if (q && q[1] === 'off') { localStorage.removeItem(ON); localStorage.removeItem(KEY); }
        else if (q) localStorage.setItem(ON, '1');
        if (!localStorage.getItem(ON)) return;
    } catch (e) { return; }

    // панель живёт в <body>, поэтому при включённом подборщике страницы грузятся целиком (без Turbo)
    var reload = document.createElement('meta'); reload.name = 'turbo-visit-control'; reload.content = 'reload'; document.head.appendChild(reload);

    function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
    function save(o) { try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {} }
    function apply(o) { for (var k in o) root.style.setProperty(k, o[k]); }
    function clearInline() { VARS.forEach(function (v) { root.style.removeProperty(v[0]); }); }
    function cur(name) { return getComputedStyle(root).getPropertyValue(name).trim(); }
    function hex6(v) {
        v = (v || '').trim();
        if (/^#[0-9a-f]{6}$/i.test(v)) return v.toLowerCase();
        if (/^#[0-9a-f]{3}$/i.test(v)) return '#' + v.slice(1).split('').map(function (c) { return c + c; }).join('').toLowerCase();
        return '#000000';
    }
    function invert(h) {
        var n = parseInt(h.slice(1), 16);
        return '#' + ('000000' + (0xFFFFFF - n).toString(16)).slice(-6);
    }

    var saved = load();
    apply(saved);

    var css = document.createElement('style');
    css.textContent =
        '#tuner{position:fixed;right:12px;bottom:12px;z-index:100000;width:260px;max-height:80vh;overflow:auto;font:13px/1.4 system-ui,sans-serif;background:#fff;color:#111;border:1px solid #888;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.5)}' +
        '#tuner *{box-sizing:border-box}#tuner h4{margin:0;padding:8px 10px;font-size:13px;cursor:pointer;background:#eee;border-radius:10px 10px 0 0}' +
        '#tuner .body{padding:8px 10px}#tuner .row{display:flex;align-items:center;gap:6px;margin:4px 0}' +
        '#tuner .row label{flex:1}#tuner input[type=color]{width:34px;height:24px;padding:0;border:1px solid #888;background:none}' +
        '#tuner input[type=text]{width:78px;font:12px monospace;padding:2px 4px}' +
        '#tuner button{font:inherit;margin:4px 4px 0 0;padding:4px 8px;border:1px solid #888;border-radius:6px;background:#f5f5f5;color:#111;cursor:pointer}' +
        '#tuner.min .body{display:none}';
    document.head.appendChild(css);

    var box = document.createElement('div'); box.id = 'tuner';
    box.innerHTML = '<h4>Цвета ▾ (клик — свернуть)</h4><div class="body"></div>';
    var body = box.querySelector('.body'), rows = {};
    box.querySelector('h4').onclick = function () { box.classList.toggle('min'); };

    VARS.forEach(function (v) {
        var row = document.createElement('div'); row.className = 'row';
        row.innerHTML = '<label></label><input type="color"><input type="text" maxlength="7">';
        row.querySelector('label').textContent = v[1];
        var pick = row.querySelector('input[type=color]'), txt = row.querySelector('input[type=text]');
        function set(val) {
            val = hex6(val); pick.value = val; txt.value = val;
            root.style.setProperty(v[0], val); saved[v[0]] = val; save(saved);
        }
        function fromText() {
            var t = txt.value.trim();
            if (/^#?[0-9a-f]{6}$/i.test(t)) {
                var val = hex6(t.charAt(0) === '#' ? t : '#' + t);
                pick.value = val; root.style.setProperty(v[0], val); saved[v[0]] = val; save(saved);
            }
        }
        pick.addEventListener('input', function () { set(pick.value); });
        pick.addEventListener('change', function () { set(pick.value); });
        txt.addEventListener('input', fromText);      // применяется сразу, как только набран 6-значный код
        txt.addEventListener('change', fromText);
        rows[v[0]] = { pick: pick, txt: txt };
        body.appendChild(row);
    });

    function sync() { VARS.forEach(function (v) { var h = hex6(cur(v[0])); rows[v[0]].pick.value = h; rows[v[0]].txt.value = h; }); }
    function btn(label, fn) { var b = document.createElement('button'); b.textContent = label; b.onclick = fn; body.appendChild(b); return b; }

    btn('Инверсия', function () {
        VARS.forEach(function (v) { var h = invert(hex6(cur(v[0]))); root.style.setProperty(v[0], h); saved[v[0]] = h; });
        save(saved); sync();
        root.style.colorScheme = root.style.colorScheme === 'light' ? 'dark' : 'light';
    });
    btn('Сбросить', function () { clearInline(); saved = {}; save(saved); root.style.colorScheme = ''; sync(); });
    btn('Копировать CSS', function () {
        var out = ':root{\n' + VARS.map(function (v) { return '    ' + v[0] + ':' + hex6(cur(v[0])) + ';'; }).join('\n') + '\n}';
        var done = function () { alert('CSS скопирован. Вставьте значения в начало app.css, в блок :root.'); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(out).then(done, function () { prompt('Скопируйте:', out); });
        else prompt('Скопируйте:', out);
    });
    btn('Выключить', function () { location.search = '?tune=off'; });

    document.body.appendChild(box);
    sync();
})();
