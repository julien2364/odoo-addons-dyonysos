/**
 * Thème Voyage pro — ajoute les deux dispositions de pied de page du thème à
 * la liste proposée par le panneau « Pied de page » de l'éditeur de site.
 * (c) DYONYSOS — https://dyonysos.fr
 */
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { FooterTemplateChoice } from "@website/builder/plugins/options/footer_template_option";

const VOYAGE_FOOTERS = [
    {
        name: "voyage_expanded",
        title: _t("Voyage — Étendu"),
        view: "theme_voyage.template_footer_voyage_expanded",
        img: "/theme_voyage/static/src/img/options/footer_voyage_expanded.png",
    },
    {
        name: "voyage_compact",
        title: _t("Voyage — Compact"),
        view: "theme_voyage.template_footer_voyage_compact",
        img: "/theme_voyage/static/src/img/options/footer_voyage_compact.png",
    },
];

export class VoyageFooterTemplatesPlugin extends Plugin {
    static id = "voyageFooterTemplates";
    resources = {
        footer_templates_providers: [
            () =>
                VOYAGE_FOOTERS.map((info) => ({
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

registry.category("website-plugins").add(VoyageFooterTemplatesPlugin.id, VoyageFooterTemplatesPlugin);
