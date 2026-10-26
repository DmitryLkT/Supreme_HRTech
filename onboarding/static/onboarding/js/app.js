// Страницы переключаются через Turbo без полной перезагрузки, поэтому всё, что привязывается
// к элементам страницы, выполняется в initPage() на каждой странице (и один раз на первой).
// Повторный вызов безопасен: уже обработанные элементы помечаются.

// Только визуализация прогресса. Сохранение данных выполняет Django.
function initRings() { document.querySelectorAll('.ring[data-progress]').forEach(ring => {
    if (ring.dataset.ready) return;
    ring.dataset.ready = "1";
    const circle = ring.querySelector('.fg');
    if (!circle) return;
    const percent = Math.max(0, Math.min(100, Number(ring.dataset.progress) || 0));
    const length = 2 * Math.PI * Number(circle.getAttribute('r'));
    circle.style.strokeDasharray = String(length);
    circle.style.strokeDashoffset = String(length);
    requestAnimationFrame(() => requestAnimationFrame(() => {
        circle.style.strokeDashoffset = String(length * (1 - percent / 100));
    }));
}); }

// Проверка ответа
function initQuestionForms() { document.querySelectorAll(".question-form").forEach(form => {
    if (form.dataset.ready) return;
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    form.dataset.ready = "1";

    const result = document.createElement("p");
    result.className = "answer-feedback";
    result.setAttribute("role", "status");
    result.setAttribute("aria-live", "polite");
    result.hidden = true;
    form.appendChild(result);

    let sending = false;

    // Убираем старый результат при выборе другого варианта.
    form.addEventListener("change", () => {
        result.hidden = true;
        result.textContent = "";
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();

        if (sending || !form.reportValidity()) return;

        sending = true;

        const originalText = button.textContent;
        const fields = form.querySelector("fieldset");

        // Собираем данные до отключения полей.
        const data = new FormData(form);

        button.disabled = true;
        button.textContent = "Проверяем…";
        if (fields) fields.disabled = true;

        result.hidden = true;
        form.setAttribute("aria-busy", "true");

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: data,
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            });

            if (response.redirected) {
                throw new Error(
                    "Возможно, сессия закончилась. Обнови страницу и войди снова."
                );
            }

            const contentType =
                response.headers.get("content-type") || "";

            if (!contentType.includes("application/json")) {
                throw new Error(
                    "Не удалось проверить ответ. Обнови страницу и попробуй снова."
                );
            }

            const answer = await response.json();

            if (!response.ok) {
                throw new Error(
                    answer.error || "Не удалось проверить ответ."
                );
            }

            result.className = answer.scored === false
                ? "answer-feedback neutral"
                : answer.is_correct
                    ? "answer-feedback success"
                    : "answer-feedback error";

            result.textContent = answer.message;
            result.hidden = false;
        } catch (error) {
            result.className = "answer-feedback error";
            result.textContent = error.message ||
                "Ошибка соединения. Попробуй ещё раз.";
            result.hidden = false;
        } finally {
            button.disabled = false;
            button.textContent = originalText;
            if (fields) fields.disabled = false;

            form.removeAttribute("aria-busy");
            sending = false;
        }
    });
}); }

// анимация страницы
function initReveal() {
    if (!document.querySelector(".checklist")) return;

    if (
        !("IntersectionObserver" in window) ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
        return;
    }

    const blocks = document.querySelectorAll(
        ".hero-step, .checklist .step, .progress-grid .card, .pulse"
    );

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-visible");
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.02,
        rootMargin: "0px 0px -40px 0px"
    });

    blocks.forEach(block => {
        if (block.getBoundingClientRect().top < window.innerHeight - 40) {
            return;
        }

        block.classList.add("reveal-on-scroll");
        observer.observe(block);
    });
}

// Крупный шрифт: выбор запоминается в браузере (если хранилище доступно)
function syncFontButton() {
    const button = document.getElementById("font-toggle");
    if (button) button.setAttribute("aria-pressed", document.documentElement.dataset.font === "large" ? "true" : "false");
}
document.addEventListener("click", event => {
    const button = event.target instanceof Element ? event.target.closest("#font-toggle") : null;
    if (!button) return;
    const root = document.documentElement;
    const large = root.dataset.font !== "large";
    if (large) root.dataset.font = "large"; else delete root.dataset.font;
    try { localStorage.setItem("altra-font", large ? "large" : "normal"); } catch (e) { /* без хранилища выбор живёт до перезагрузки */ }
    syncFontButton();
});

// Защита от двойной отправки обычных (не Turbo) форм: кнопка блокируется после старта отправки
window.addEventListener("pageshow", () => {
    document.querySelectorAll('button[aria-busy="true"]').forEach(b => {
        b.disabled = false; b.removeAttribute("aria-busy");
    });
});
document.addEventListener("submit", event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.classList.contains("question-form")) return;
    const button = form.querySelector('button[type="submit"].btn');
    if (!button) return;
    setTimeout(() => {
        if (event.defaultPrevented) return;   // отправкой занялся Turbo (см. turbo:submit-start)
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
    }, 0);
});

// ---- Бесшовные переходы (Turbo Drive) ----
// Форма отправляется без перезагрузки: показываем состояние «в процессе» на кнопке.
document.addEventListener("turbo:submit-start", event => {
    const submitter = event.detail && event.detail.formSubmission && event.detail.formSubmission.submitter;
    if (submitter) submitter.setAttribute("aria-busy", "true");
});
document.addEventListener("turbo:submit-end", event => {
    const submitter = event.detail && event.detail.formSubmission && event.detail.formSubmission.submitter;
    if (submitter) submitter.removeAttribute("aria-busy");
});

// Ошибочные ответы на обычные переходы (404, 403, 500) и редирект на вход открываем обычной загрузкой:
// у этих страниц своя вёрстка и свои стили, их не нужно подмешивать в открытую страницу.
// Ответы на формы (например, 400 с подсказкой об ошибке) Turbo показывает сам.
document.addEventListener("turbo:before-fetch-response", event => {
    if (event.target instanceof HTMLFormElement) return;
    const response = event.detail.fetchResponse;
    const toLogin = response.redirected && /^\/login\//.test(response.location.pathname);
    if (response.statusCode >= 400 || toLogin) {
        event.preventDefault();
        window.location.assign(response.location.href);
    }
});

function initPage() {
    syncFontButton();
    initRings();
    initQuestionForms();
    initReveal();
}
document.addEventListener("turbo:load", initPage);
document.addEventListener("turbo:render", () => {
    syncFontButton();
    // после перехода переносим фокус на содержимое: экранный диктор читает новую страницу
    const main = document.getElementById("main-content");
    if (main) main.focus({ preventScroll: true });
});
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initPage);
else initPage();
