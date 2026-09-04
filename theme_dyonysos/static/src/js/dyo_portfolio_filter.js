/**
 * Agence B2B — filtres du bloc « Portfolio ».
 *
 * Filtrage côté client, sans dépendance : un clic sur un bouton
 * `[data-dyo-filter]` masque les éléments `[data-dyo-category]` qui ne
 * correspondent pas. La valeur `*` réaffiche tout.
 *
 * (c) DYONYSOS — https://dyonysos.fr
 */
(function () {
    "use strict";

    document.addEventListener("click", function (ev) {
        var button = ev.target.closest && ev.target.closest(".o_dyo_filter");
        if (!button) {
            return;
        }
        var section = button.closest(".s_dyo_portfolio");
        if (!section) {
            return;
        }
        ev.preventDefault();

        var wanted = button.getAttribute("data-dyo-filter") || "*";
        section.querySelectorAll(".o_dyo_filter").forEach(function (el) {
            var active = el === button;
            el.classList.toggle("is-active", active);
            el.setAttribute("aria-pressed", String(active));
        });
        section.querySelectorAll(".o_dyo_portfolio_item").forEach(function (item) {
            var category = item.getAttribute("data-dyo-category");
            item.classList.toggle("is-hidden", wanted !== "*" && category !== wanted);
        });
    });
})();
