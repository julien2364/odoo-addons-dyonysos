#!/usr/bin/env bash
# Vérification finale : installation sur base neuve, application du thème,
# rendu des pages et compilation réelle du SCSS, pour les six modules.
cd /home/claude
GLOBAL=0
for T in theme_presse_lite theme_presse theme_voyage_lite theme_voyage theme_animalerie_lite theme_animalerie; do
  echo "══════════════════════════════════ $T"
  dropdb --if-exists themetest >/dev/null 2>&1
  OUT=$(python3 odoo19/odoo-bin -c odoo.conf -d themetest -i website,$T --without-demo=all \
        --stop-after-init --log-level=warn 2>&1 | grep -E "ERROR|CRITICAL|ParseError|Traceback" -A5 | head -20)
  if [ -z "$OUT" ]; then echo "  ✓ installation sur base neuve : aucune erreur, aucun warning de vue";
  else echo "  ✗ installation :"; echo "$OUT"; GLOBAL=1; fi
  bash apply.sh themetest $T | sed 's/^/  /'
  case "$T" in
    theme_presse_lite)      PAGES="/ /magazine /blog";;
    theme_presse)           PAGES="/ /magazine /rubrique-economie /auteur-camille-ferrand /blog";;
    theme_voyage_lite)      PAGES="/ /nos-voyages";;
    theme_voyage)           PAGES="/ /nos-voyages /destination-vantour /itineraire-cretes-de-vantour";;
    theme_animalerie_lite)  PAGES="/ /notre-boutique /shop";;
    theme_animalerie)       PAGES="/ /notre-boutique /categorie-chiens /shop";;
  esac
  bash check_theme.sh themetest $PAGES || GLOBAL=1
done
dropdb --if-exists themetest >/dev/null 2>&1
echo
[ $GLOBAL -eq 0 ] && echo "VÉRIFICATION GLOBALE : OK" || echo "VÉRIFICATION GLOBALE : ÉCHEC"
exit $GLOBAL
