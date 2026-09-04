/**
 * Thème Presse pro — bascule du mode sombre.
 *
 * Tout élément portant la classe `o_presse_dark_toggle` bascule la classe
 * `o_presse_dark` sur <html>. Le choix est conservé dans le stockage local du
 * visiteur et réappliqué au chargement suivant. Aucun appel réseau.
 *
 * (c) DYONYSOS — https://dyonysos.fr
 */
(function () {
    "use strict";

    var KEY = "presse-color-scheme";
    var root = document.documentElement;

    function read() {
        try {
            return window.localStorage.getItem(KEY);
        } catch (e) {
            return null;
        }
    }

    function write(value) {
        try {
            window.localStorage.setItem(KEY, value);
        } catch (e) {
            // Stockage indisponible (navigation privée, cookies refusés) :
            // la bascule reste valable pour la page en cours.
        }
    }

    function apply(mode) {
        var dark = mode === "dark";
        root.classList.toggle("o_presse_dark", dark);
        root.classList.toggle("o_presse_light", mode === "light");
        Array.prototype.forEach.call(
            document.querySelectorAll(".o_presse_dark_toggle"),
            function (el) {
                el.setAttribute("aria-pressed", String(dark));
                var label = el.querySelector("[data-presse-dark-label]");
                if (label) {
                    label.textContent = dark ? "Mode clair" : "Mode sombre";
                }
            }
        );
    }

    var stored = read();
    if (stored === "dark" || stored === "light") {
        apply(stored);
    }

    document.addEventListener("click", function (ev) {
        var toggle = ev.target.closest && ev.target.closest(".o_presse_dark_toggle");
        if (!toggle) {
            return;
        }
        ev.preventDefault();
        var next = root.classList.contains("o_presse_dark") ? "light" : "dark";
        apply(next);
        write(next);
    });
})();
