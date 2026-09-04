# -*- coding: utf-8 -*-
"""Construit une page de démonstration (theme.ir.ui.view + theme.website.page)
en reprenant le markup des blocs. La duplication entre views/snippets/*.xml et
data/pages.xml est imposée par Odoo : le bloc glissable et la section éditable
dans l'oe_structure sont deux objets distincts."""
import re, sys, os

def sections(path):
    src = open(path, encoding="utf-8").read()
    m = re.search(r"<template[^>]*>(.*)</template>", src, re.S)
    body = m.group(1)
    # on retire l'indentation d'origine de 4 espaces pour reformater proprement
    return body.strip()

def build(module, out, pages):
    parts = ['<?xml version="1.0" encoding="utf-8"?>', "<odoo>", "",
             "<!-- Pages de démonstration. Dans un module theme_*, <template> devient",
             "     une theme.ir.ui.view et la page une theme.website.page : elles ne",
             "     sont créées dans le site qu'à l'application du thème. Le markup est",
             "     volontairement dupliqué depuis views/snippets/ pour que les sections",
             "     soient éditables dans l'oe_structure de la page. -->", ""]
    for tpl_id, name, url, files, intro in pages:
        parts.append(f'<template id="{tpl_id}" name="{name}">')
        parts.append('    <t t-call="website.layout">')
        parts.append('        <div id="wrap" class="oe_structure oe_empty">')
        if intro:
            parts.append(intro)
        for f in files:
            block = sections(f)
            parts.append("\n".join("            " + ln if ln.strip() else ln
                                   for ln in block.splitlines()))
        parts.append("        </div>")
        parts.append("    </t>")
        parts.append("</template>")
        parts.append("")
        parts.append(f'<record id="{tpl_id}_website_page" model="theme.website.page">')
        parts.append(f'    <field name="url">{url}</field>')
        parts.append(f'    <field name="view_id" ref="{tpl_id}"/>')
        parts.append('    <field name="is_published" eval="True"/>')
        parts.append("</record>")
        parts.append("")
    parts += ["</odoo>", ""]
    open(out, "w", encoding="utf-8").write("\n".join(parts))
    print("écrit", out)
