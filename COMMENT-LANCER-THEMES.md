# Thèmes Odoo 19 DYONYSOS — comment lancer le projet

Trois thèmes de site web Odoo 19, chacun en deux modules : une version gratuite
(LGPL-3) et une version pro (OPL-1) qui en dépend.

| Module | Licence | Prix | Dépendances |
| --- | --- | --- | --- |
| `theme_presse_lite` | LGPL-3 | gratuit | `website`, `website_blog` |
| `theme_presse` | OPL-1 | 345,00 € | `theme_presse_lite` |
| `theme_voyage_lite` | LGPL-3 | gratuit | `website` |
| `theme_voyage` | OPL-1 | 179,10 € | `theme_voyage_lite` |
| `theme_animalerie_lite` | LGPL-3 | gratuit | `website`, `website_sale` |
| `theme_animalerie` | OPL-1 | 345,00 € | `theme_animalerie_lite` |

---

## 1. Prérequis

- Python 3.10 ou plus récent, PostgreSQL 14 ou plus récent
- Les sources d'Odoo 19 (branche `19.0`)
- Un rôle PostgreSQL portant le nom de l'utilisateur système, avec `CREATEDB`

```bash
git clone --depth 1 --branch 19.0 https://github.com/odoo/odoo.git odoo19
sudo apt-get install -y build-essential python3-dev libpq-dev libldap2-dev \
    libsasl2-dev libxml2-dev libxslt1-dev libjpeg-dev
pip install --break-system-packages --prefer-binary -r odoo19/requirements.txt
```

Deux paquets de `requirements.txt` ne se compilent pas avec le `setuptools` de
Debian/Ubuntu (`AttributeError: install_layout`). Le contournement :

```bash
pip install --break-system-packages --ignore-installed -U "setuptools<81" wheel
pip install --break-system-packages psycopg2-binary rjsmin
```

`ofxparse` et `vobject` ne servent qu'à la compta OFX et aux fichiers vCard :
ils ne sont pas nécessaires pour travailler sur les thèmes.

## 2. Configuration

Fichier `odoo.conf`, à côté du dossier `odoo19` :

```ini
[options]
addons_path = /chemin/vers/odoo19/addons,/chemin/vers/addons-dyonysos
data_dir = ~/.local/share/Odoo
db_user = <votre utilisateur>
list_db = True
http_interface = 127.0.0.1
http_port = 8069
limit_time_cpu = 900
limit_time_real = 1800
```

```bash
sudo service postgresql start
```

## 3. Installer un thème sur une base neuve

```bash
dropdb --if-exists themetest
python3 odoo19/odoo-bin -c odoo.conf -d themetest -i website,theme_presse \
    --without-demo=all --stop-after-init --log-level=warn 2>&1 \
    | grep -E "ERROR|CRITICAL|ParseError|Traceback" -A5 | head -20
```

Aucune sortie = installation propre.

## 4. Appliquer le thème et regarder le résultat

**Installer un module de thème ne l'applique pas.** Les pages de démonstration et
les blocs ne deviennent visibles qu'à l'application.

En ligne de commande :

```bash
bash apply.sh themetest theme_presse
```

ou, dans l'interface : *Site web → Configuration → Thème → Choisir*.

Puis :

```bash
python3 odoo19/odoo-bin -c odoo.conf -d themetest --http-port=8069
```

et ouvrir <http://127.0.0.1:8069/> — identifiants par défaut `admin` / `admin`.

Pages de démonstration créées par chaque thème :

| Thème | Pages |
| --- | --- |
| `theme_presse_lite` | `/magazine`, plus les vues du blog (`/blog`) |
| `theme_presse` | `/rubrique-economie`, `/auteur-camille-ferrand` |
| `theme_voyage_lite` | `/nos-voyages` |
| `theme_voyage` | `/destination-vantour`, `/itineraire-cretes-de-vantour` |
| `theme_animalerie_lite` | `/notre-boutique`, plus la boutique (`/shop`) |
| `theme_animalerie` | `/categorie-chiens` |

## 5. Vérifier

```bash
# contrôle statique du dépôt (manifestes, fichiers obligatoires, XML, marques)
bash addons-dyonysos/scripts/lint.sh

# installation + application + rendu + compilation SCSS des six modules
bash verify_all.sh
```

`check_theme.sh` mérite une explication : **une erreur SCSS ne remonte pas dans
les logs Odoo**. Le serveur sert alors un bundle de repli contenant le message
`## CSS error message ##`. Le script télécharge le bundle et cherche cette chaîne :
c'est le seul moyen fiable de détecter une régression de feuille de styles.

## 6. Traductions

```bash
python3 odoo19/odoo-bin i18n export -c odoo.conf -d <base> <module>
```

Le fichier `.pot` est écrit dans `<module>/i18n/`. La langue source de ces
thèmes étant le français, `i18n/fr.po` reprend le modèle entrée par entrée.

## 7. Arborescence d'un thème

```
theme_xxx_lite/
├── __manifest__.py            # version, licence, dépendances, assets
├── LICENSE, COPYRIGHT
├── images/main_screenshot.png # capture principale de la fiche
├── static/description/        # icône, maquettes, index.html de la fiche
├── static/src/scss/
│   ├── primary_variables.scss # palettes et polices → web._assets_primary_variables
│   └── theme.scss             # habillage → web.assets_frontend
├── static/src/img/            # visuels et vignettes de blocs (générés avec PIL)
├── views/snippets/            # un bloc = un <template>, + snippets.xml
├── data/pages.xml             # theme.website.page + theme.ir.ui.view
└── i18n/
```

## 8. Pièges Odoo 19 à connaître avant de modifier

1. **Ordre des assets.** Le fichier `primary_variables.scss` du thème doit être
   ajouté **après** celui de `website` : en `('prepend', …)`, `$o-theme-font-configs`
   et `$o-color-palettes` n'existent pas encore et la compilation échoue.
2. **Un thème payant n'hérite pas du SCSS du thème gratuit dont il dépend.**
   Odoo n'assemble que les assets du thème *appliqué*. Le manifeste du thème pro
   redéclare explicitement les fichiers SCSS du thème gratuit.
3. **libsass, pas dart-sass.** `clamp(2rem, 1.1rem + 3.2vw, 3.6rem)` échoue
   (« Incompatible units ») : il faut `calc(1.1rem + 3.2vw)` au milieu. De même
   `min(92vw, 1200px)` est évalué comme la fonction Sass `min()` — protéger avec
   `#{"min(92vw, 1200px)"}`. Et ne pas mélanger `px` et `rem` dans une même
   valeur de `$o-website-values-palettes`.
4. **`hasclass()` ne marche pas sur les classes posées par `t-attf-class`.**
   Les vues de `website_blog` et `website_sale` en posent beaucoup : viser un
   `t-set` ou un `id` comme ancre d'`xpath`.
5. **Dans un module `theme_*`, tout `<template>` devient une `theme.ir.ui.view`**
   (`odoo/tools/convert.py`). Les pages se déclarent donc en `theme.website.page`,
   pas en `website.page`, et ne sont créées qu'à l'application du thème.
6. **La duplication du markup est normale.** Le contenu d'un bloc existe deux
   fois : dans `views/snippets/*.xml` (le bloc glissable) et dans `data/pages.xml`
   (la section éditable dans l'`oe_structure`). C'est le fonctionnement d'Odoo.
7. **`<list>` remplace `<tree>`** en Odoo 19 ; le linter du dépôt le vérifie.

---

*DYONYSOS — welcome@dyonysos.fr — https://dyonysos.fr*
