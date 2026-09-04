/**
 * Thème Animalerie pro — ajoute les deux dispositions de pied de page du thème à
 * la liste proposée par le panneau « Pied de page » de l'éditeur de site.
 * (c) DYONYSOS — https://dyonysos.fr
 */
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { FooterTemplateChoice } from "@website/builder/plugins/options/footer_template_option";

const ANIM_FOOTERS = [
    {
        name: "anim_expanded",
        title: _t("Animalerie — Étendu"),
        view: "theme_animalerie.template_footer_anim_expanded",
        img: "/theme_animalerie/static/src/img/options/footer_anim_expanded.png",
    },
    {
        name: "anim_compact",
        title: _t("Animalerie — Compact"),
        view: "theme_animalerie.template_footer_anim_compact",
        img: "/theme_animalerie/static/src/img/options/footer_anim_compact.png",
    },
];

export class AnimFooterTemplatesPlugin extends Plugin {
    static id = "animFooterTemplates";
    resources = {
        footer_templates_providers: [
            () =>
                ANIM_FOOTERS.map((info) => ({
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

registry.category("website-plugins").add(AnimFooterTemplatesPlugin.id, AnimFooterTemplatesPlugin);
