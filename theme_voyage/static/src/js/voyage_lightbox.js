/* Thème Voyage pro — lightbox de la galerie mosaïque.
   JavaScript simple, sans dépendance : la lightbox n'est créée qu'au premier
   clic et se ferme à l'Échap, au clic sur le fond ou sur le bouton. Le script
   reste inerte dans l'éditeur de site. */
(function () {
    "use strict";

    function inEditor() {
        return document.body.classList.contains("editor_enable")
            || document.body.classList.contains("o_edit_mode")
            || !!document.querySelector(".o_website_editor, #oe_snippets");
    }

    var overlay = null;
    var lastFocus = null;

    function close() {
        if (!overlay) {
            return;
        }
        overlay.remove();
        overlay = null;
        document.removeEventListener("keydown", onKey);
        if (lastFocus) {
            lastFocus.focus();
        }
    }

    function onKey(ev) {
        if (ev.key === "Escape") {
            close();
        }
    }

    function open(src, alt) {
        close();
        lastFocus = document.activeElement;
        overlay = document.createElement("div");
        overlay.className = "o_voyage_lightbox";
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        overlay.setAttribute("aria-label", alt || "Photo en grand format");

        var img = document.createElement("img");
        img.src = src;
        img.alt = alt || "";

        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "o_voyage_lightbox_close";
        btn.setAttribute("aria-label", "Fermer");
        btn.textContent = "×";
        btn.addEventListener("click", close);

        overlay.appendChild(img);
        overlay.appendChild(btn);
        overlay.addEventListener("click", function (ev) {
            if (ev.target === overlay) {
                close();
            }
        });
        document.body.appendChild(overlay);
        document.addEventListener("keydown", onKey);
        btn.focus();
    }

    function start() {
        if (inEditor()) {
            return;
        }
        var tiles = document.querySelectorAll(".o_voyage_tile");
        Array.prototype.forEach.call(tiles, function (tile) {
            tile.addEventListener("click", function () {
                var img = tile.querySelector("img");
                if (img) {
                    open(img.getAttribute("data-full") || img.src, img.alt);
                }
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
