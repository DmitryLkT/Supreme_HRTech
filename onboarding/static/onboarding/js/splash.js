(function () {
    var splash = document.getElementById('splash');
    var root = document.documentElement;
    if (!splash) return;
    if (!root.classList.contains('splash-on')) { splash.remove(); return; }

    var video = splash.querySelector('video');
    var skip = document.getElementById('splash-skip');
    var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

    var MAX_MS = 6000;                 // жёсткий предел показа, даже если видео не загрузилось
    var STILL_MS = reduced ? 900 : 1500; // сколько показывать постер, если видео не играет
    var finished = false;
    var stillTimer = null;

    function finish() {
        if (finished) return;
        finished = true;
        clearTimeout(stillTimer);
        try { sessionStorage.setItem('altra-splash', '1'); } catch (e) {}
        splash.classList.add('splash-hide');
        setTimeout(function () {
            root.classList.remove('splash-on');
            splash.remove();
        }, 600);
    }

    // Видео не воспроизводится (ошибка, запрет автозапуска, «уменьшить движение»): показываем постер и уходим
    function showStill() {
        clearTimeout(stillTimer);
        stillTimer = setTimeout(finish, STILL_MS);
    }

    if (video && !reduced) {
        video.addEventListener('ended', finish);
        video.addEventListener('error', showStill);
        var started;
        try { started = video.play(); } catch (e) { showStill(); }
        if (started && started.catch) started.catch(showStill);
    } else {
        showStill();
    }

    setTimeout(finish, MAX_MS);
    splash.addEventListener('click', finish);                       // клик пропускает заставку
    if (skip) skip.addEventListener('click', finish);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') finish(); });
})();
