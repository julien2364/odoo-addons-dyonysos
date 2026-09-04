/* Thème Presse pro — sommaire automatique et mode lecture.
   Script volontairement écrit en JavaScript simple (pas de module Odoo) :
   il n'a besoin ni du registre ni du framework, et reste inerte dans
   l'éditeur de site. */
(function () {
    "use strict";

    function inEditor() {
        return document.body.classList.contains("editor_enable")
            || document.body.classList.contains("o_edit_mode")
            || !!document.querySelector(".o_website_editor, #oe_snippets");
    }

    function slugify(text, index) {
        var base = (text || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "");
        return (base || "section") + "-" + index;
    }

    function buildToc() {
        var holder = document.querySelector("[data-presse-toc]");
        if (!holder) {
            return;
        }
        var scope = document.querySelector(
            ".o_presse_article, .o_wblog_post_content_field, .o_wblog_post_content");
        if (!scope) {
            holder.remove();
            return;
        }
        var headings = scope.querySelectorAll("h2, h3");
        if (headings.length < 2) {
            holder.remove();
            return;
        }
        var nav = document.createElement("nav");
        nav.className = "o_presse_toc";
        nav.setAttribute("aria-label", "Sommaire de l'article");
        var title = document.createElement("p");
        title.className = "o_presse_toc_title";
        title.textContent = "Dans cet article";
        var list = document.createElement("ol");
        Array.prototype.forEach.call(headings, function (h, i) {
            if (!h.id) {
                h.id = slugify(h.textContent, i + 1);
            }
            var li = document.createElement("li");
            if (h.tagName === "H3") {
                li.className = "o_presse_toc_h3";
            }
            var a = document.createElement("a");
            a.href = "#" + h.id;
            a.textContent = h.textContent.trim();
            li.appendChild(a);
            list.appendChild(li);
        });
        nav.appendChild(title);
        nav.appendChild(list);
        holder.replaceWith(nav);
    }

    function bindReadingMode() {
        var toggles = document.querySelectorAll("[data-presse-reader]");
        if (!toggles.length) {
            return;
        }
        Array.prototype.forEach.call(toggles, function (btn) {
            btn.setAttribute("aria-pressed", "false");
            btn.addEventListener("click", function () {
                var on = document.body.classList.toggle("o_presse_reading");
                btn.setAttribute("aria-pressed", on ? "true" : "false");
                btn.textContent = on ? "Quitter le mode lecture" : "Mode lecture";
            });
        });
    }

    function bindFilters() {
        var blocks = document.querySelectorAll(".s_presse_rubriques");
        Array.prototype.forEach.call(blocks, function (block) {
            var buttons = block.querySelectorAll(".o_presse_filter");
            var items = block.querySelectorAll(".o_presse_item");
            if (!buttons.length || !items.length) {
                return;
            }
            Array.prototype.forEach.call(buttons, function (btn) {
                btn.addEventListener("click", function () {
                    var wanted = btn.getAttribute("data-presse-filter") || "*";
                    Array.prototype.forEach.call(buttons, function (b) {
                        b.classList.toggle("active", b === btn);
                        b.setAttribute("aria-pressed", b === btn ? "true" : "false");
                    });
                    Array.prototype.forEach.call(items, function (item) {
                        var cat = item.getAttribute("data-presse-category") || "";
                        item.hidden = !(wanted === "*" || cat === wanted);
                    });
                });
            });
        });
    }

    function start() {
        if (inEditor()) {
            return;
        }
        buildToc();
        bindReadingMode();
        bindFilters();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
