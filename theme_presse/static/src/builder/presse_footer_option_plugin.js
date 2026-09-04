/**
 * Thème Presse pro — ajoute les deux dispositions de pied de page du thème à
 * la liste proposée par le panneau « Pied de page » de l'éditeur de site.
 * (c) DYONYSOS — https://dyonysos.fr
 */
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { FooterTemplateChoice } from "@website/builder/plugins/options/footer_template_option";

const PRESSE_FOOTERS = [
    {
        name: "presse_expanded",
        title: _t("Presse — Étendu"),
        view: "theme_presse.template_footer_presse_expanded",
        img: "/theme_presse/static/src/img/options/footer_presse_expanded.png",
    },
    {
        name: "presse_compact",
        title: _t("Presse — Compact"),
        view: "theme_presse.template_footer_presse_compact",
        img: "/theme_presse/static/src/img/options/footer_presse_compact.png",
    },
];

export class PresseFooterTemplatesPlugin extends Plugin {
    static id = "presseFooterTemplates";
    resources = {
        footer_templates_providers: [
            () =>
                PRESSE_FOOTERS.map((info) => ({
                    key: info.name,
                    Component: FooterTemplateChoice,
                    props: {
                        imgSrc: info.img,
                        varName: info.name,
                        view: info.view,
                        title: info.title,
                    },
                })),
        ],
    };
}

registry.category("website-plugins").add(PresseFooterTemplatesPlugin.id, PresseFooterTemplatesPlugin);
