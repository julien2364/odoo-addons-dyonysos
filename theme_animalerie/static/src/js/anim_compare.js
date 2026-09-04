/* Thème Animalerie pro — sélecteur par animal et comparateur.
   JavaScript simple, sans dépendance, inerte dans l'éditeur de site. */
(function () {
    "use strict";

    function inEditor() {
        return document.body.classList.contains("editor_enable")
            || document.body.classList.contains("o_edit_mode")
            || !!document.querySelector(".o_website_editor, #oe_snippets");
    }

    function bindSelector() {
        var blocks = document.querySelectorAll(".s_anim_selecteur");
        Array.prototype.forEach.call(blocks, function (block) {
            var tabs = block.querySelectorAll(".o_anim_species");
            var panes = block.querySelectorAll(".o_anim_species_pane");
            if (!tabs.length || !panes.length) {
                return;
            }
            Array.prototype.forEach.call(tabs, function (tab) {
                tab.addEventListener("click", function () {
                    var key = tab.getAttribute("data-anim-species");
                    Array.prototype.forEach.call(tabs, function (t) {
                        var on = t === tab;
                        t.classList.toggle("active", on);
                        t.setAttribute("aria-selected", on ? "true" : "false");
                    });
                    Array.prototype.forEach.call(panes, function (pane) {
                        pane.hidden = pane.getAttribute("data-anim-species") !== key;
                    });
                });
            });
        });
    }

    function bindCompare() {
        var blocks = document.querySelectorAll(".s_anim_comparateur");
        Array.prototype.forEach.call(blocks, function (block) {
            var boxes = block.querySelectorAll("[data-anim-compare]");
            var cols = block.querySelectorAll("[data-anim-column]");
            if (!boxes.length || !cols.length) {
                return;
            }
            function refresh() {
                var kept = [];
                Array.prototype.forEach.call(boxes, function (b) {
                    if (b.checked) {
                        kept.push(b.getAttribute("data-anim-compare"));
                    }
                });
                if (!kept.length) {
                    kept = null;
                }
                Array.prototype.forEach.call(cols, function (col) {
                    var key = col.getAttribute("data-anim-column");
                    col.hidden = !!(kept && kept.indexOf(key) === -1);
                });
            }
            Array.prototype.forEach.call(boxes, function (b) {
                b.addEventListener("change", refresh);
            });
            refresh();
        });
    }

    function start() {
        if (inEditor()) {
            return;
        }
        bindSelector();
        bindCompare();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
