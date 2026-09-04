/**
 * Agence B2B — ajoute les deux dispositions de pied de page du thème à la
 * liste proposée par le panneau « Pied de page » de l'éditeur de site.
 * (c) DYONYSOS — https://dyonysos.fr
 */
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { FooterTemplateChoice } from "@website/builder/plugins/options/footer_template_option";

const DYO_FOOTERS = [
    {
        name: "dyo_expanded",
        title: _t("Agence B2B — Étendu"),
        view: "theme_dyonysos.template_footer_dyo_expanded",
        img: "/theme_dyonysos/static/src/img/options/footer_dyo_expanded.png",
    },
    {
        name: "dyo_compact",
        title: _t("Agence B2B — Compact"),
        view: "theme_dyonysos.template_footer_dyo_compact",
        img: "/theme_dyonysos/static/src/img/options/footer_dyo_compact.png",
    },
];

export class DyoFooterTemplatesPlugin extends Plugin {
    static id = "dyoFooterTemplates";
    resources = {
        footer_templates_providers: [
            () =>
                DYO_FOOTERS.map((info) => ({
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

registry.category("website-plugins").add(DyoFooterTemplatesPlugin.id, DyoFooterTemplatesPlugin);
