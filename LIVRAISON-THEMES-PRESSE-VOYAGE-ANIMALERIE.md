# Livrable — trois thèmes Odoo 19 originaux, gratuit + pro

**DYONYSOS (Julien Daures) — 4 septembre 2026**
Dépôt : `addons-dyonysos/` — 238 fichiers, 5,2 Mo.

---

## 0. Contexte : environnement reconstruit

Le conteneur de la session était vierge : ni `odoo19`, ni `addons-dyonysos`, donc
ni les deux thèmes livrés qui devaient servir de modèle (`theme_dyonysos_lite`,
`theme_dyonysos`), ni `scripts/lint.sh`, ni `make_assets.py`, ni les six modules
de non-régression. Aucune sauvegarde du dépôt n'a été trouvée sur le Drive.

Ont donc été reconstruits : les sources Odoo 19 (clone de la branche `19.0`), les
dépendances Python, PostgreSQL, `odoo.conf`, `scripts/lint.sh` (réécrit d'après
les conventions du brief), `make_assets.py` (helpers PIL `icon`, `banner`,
`screenshot_card`, plus des primitives de dessin), et le wordmark DYONYSOS.

Les conventions du dépôt ont été reprises **du brief**, pas du code des deux
thèmes livrés — c'est la principale différence avec la mission telle qu'écrite.

---

## 1. Ce qui a été produit

| Module | Licence | Prix | Dépendances | Blocs | Fichiers |
| --- | --- | --- | --- | --- | --- |
| `theme_presse_lite` | LGPL-3 | gratuit | `website`, `website_blog` | 4 | 32 |
| `theme_presse` | OPL-1 | 345,00 € | `theme_presse_lite` | 7 | 39 |
| `theme_voyage_lite` | LGPL-3 | gratuit | `website` | 4 | 33 |
| `theme_voyage` | OPL-1 | 179,10 € | `theme_voyage_lite` | 7 | 43 |
| `theme_animalerie_lite` | LGPL-3 | gratuit | `website`, `website_sale` | 3 | 41 |
| `theme_animalerie` | OPL-1 | 345,00 € | `theme_animalerie_lite` | 7 | 39 |

Chaque module contient : `__manifest__.py`, `LICENSE`, `COPYRIGHT`,
`images/main_screenshot.png`, `static/description/` (icône, 3 ou 4 maquettes,
`index.html` en français), `static/src/scss/primary_variables.scss` et
`theme.scss`, les visuels et vignettes de blocs, `views/snippets/`, `data/`,
et `i18n/` (`.pot` + `fr.po`).

---

## 2. Thème Presse — magazine et presse en ligne

**Direction artistique.** Playfair Display pour les titres, Inter pour le texte,
échelle typographique marquée (h1 ×3,4), filets fins, palette noir anthracite
`#1F2933` / rouge éditorial `#B3121D` / crème `#FBF8F3`. Largeur de lecture
limitée à 68 caractères sur les articles.

**Version gratuite.** Système de design complet ; gabarit d'article (chapô,
intertitres, citations, légendes, temps de lecture estimé à partir du contenu
réel) ; blocs *Une*, *Grille d'articles*, *À lire aussi*, *Gabarit d'article* ;
habillage des vues de `website_blog` (les vues sont stylées, jamais remplacées ;
une seule information est ajoutée : rubrique + temps de lecture) ; page de
démonstration `/magazine` ; 3 rubriques et 12 articles fictifs.

**Version pro.** Une multi-niveaux (1 principal + 4 secondaires), fil
d'actualité, grille par rubrique avec filtres, dossier/série, encadré auteur,
chronologie, bandeau newsletter ; pages `/rubrique-economie` et
`/auteur-camille-ferrand` ; sommaire automatique des intertitres et mode lecture
(JavaScript sans dépendance) ; une palette crème supplémentaire.

**Limites honnêtes.**
- Le bloc *Une* et la grille sont **du markup éditable, pas des listes
  dynamiques** : ils n'interrogent pas `blog.post`. Un rédacteur choisit ses
  articles à la main. Pour une une automatique, il faut utiliser en complément
  les blocs `s_blog_posts_*` fournis par Odoo.
- Les filtres de rubrique agissent sur les cartes présentes dans le bloc, pas sur
  une requête serveur : au-delà d'une trentaine de cartes, mieux vaut la page
  `/blog` d'Odoo et ses filtres natifs.
- Le temps de lecture est une estimation (nombre de mots ÷ 200), calculée en
  QWeb, sans champ stocké : il n'est pas éditable article par article.
- Les 12 articles de démonstration sont créés **à l'installation du module**
  (les `blog.post` ne sont pas des objets de thème). Sur une base de production,
  il faut les supprimer.
- Le sommaire et le mode lecture ne s'affichent que sur les articles du blog,
  pas sur une page libre.

---

## 3. Thème Voyage — carnet de voyage et tourisme

**Direction artistique.** Poppins pour les titres, Inter pour le texte, palette
sable `#FAF3E8` / terracotta `#A8452A` / bleu profond `#123A5E`, coins arrondis
1,25 rem, ombres douces, boutons en pilule.

**Version gratuite.** Système de design ; bandeau d'accueil pleine hauteur avec
voile de lisibilité ; grille de destinations (6 cartes) ; récit en deux colonnes
texte/image ; appel à l'action ; page `/nos-voyages`.

**Version pro.** Carte d'itinéraire par étapes, galerie mosaïque avec lightbox
(fermeture à l'Échap, au clic sur le fond, focus rendu), fiche destination
(durée, budget, saison, difficulté sur 4 crans), témoignages, calendrier de
départs avec pastilles d'état, formulaire de demande de devis, carnet de bord
chronologique ; pages `/destination-vantour` et `/itineraire-cretes-de-vantour` ;
une palette sombre supplémentaire.

**Limites honnêtes.**
- **Il n'y a pas de vraie carte.** Le « tracé d'itinéraire » est une illustration
  générée, pas une carte interactive : aucun fond cartographique n'est embarqué
  (ce serait une dépendance externe et une question de licence). Pour une carte
  réelle, il faut brancher un service tiers.
- Le calendrier de départs et la fiche destination sont **statiques** : ni
  `product.template`, ni `event.event` derrière. Les dates et les places se
  saisissent à la main dans l'éditeur.
- Le formulaire de devis est un gabarit HTML : il n'envoie rien tant qu'il n'est
  pas relié au module Formulaires d'Odoo ou à un service externe.
- La lightbox affiche l'image telle qu'elle est dans la page : pas de version
  haute définition séparée (l'attribut `data-full` est prévu mais non alimenté
  par la démo), pas de navigation entre les photos.

---

## 4. Thème Animalerie — boutique en ligne

Aucune référence à la marque du client : **ni le nom, ni le logo, ni les visuels
« Pet Stone »**. La marque de démonstration `Trèfle & Museau` est inventée. Le
linter du dépôt vérifie l'absence de la chaîne interdite à chaque passage.

**Direction artistique.** Poppins pour les titres, Nunito pour le texte, palette
vert naturel `#2F6B3C` / terracotta `#A9502F` / ivoire `#FBF7F0`, coins très
arrondis (1,5 rem), illustrations générées (silhouettes stylisées, motifs de
pattes, formes organiques).

**Version gratuite.** Système de design ; page d'accueil boutique ; grille de
produits stylée ; fiche produit retravaillée avec encart de promesse (expédition,
retour, conseil) ; bandeau de réassurance ; habillage de `website_sale` (grille,
fiche, panier) ; page `/notre-boutique` ; 12 produits et 3 catégories fictifs
avec visuels générés.

**Version pro.** Sélecteur par type d'animal (3 onglets), comparateur de produits
(colonnes masquables), avis clients avec note moyenne et répartition, guide de
tailles, offre d'abonnement (3 formules), blocs conseils, mise en avant de
promotions, panier et tunnel de commande stylés, page catégorie enrichie
`/categorie-chiens` ; une palette sombre supplémentaire.

**Limites honnêtes.**
- Le comparateur, les avis, le guide de tailles et l'abonnement sont **du contenu
  éditable, pas des données produit**. Les avis ne viennent pas de
  `rating.rating`, l'abonnement ne crée pas de `sale.subscription`, le
  comparateur ne lit pas les attributs des produits. Ce sont des blocs de mise en
  page ; le branchement métier reste à faire.
- Les 12 produits de démonstration sont créés **à l'installation du module** :
  sur une base de production, il faut les supprimer, ou installer d'abord sur une
  base de test.
- L'habillage du panier et du tunnel de commande passe par des sélecteurs CSS sur
  les vues d'Odoo. C'est le point le plus fragile du lot : une refonte des vues
  de `website_sale` dans une version mineure peut demander une reprise.
- La fiche produit n'est pas réécrite : seul un encart est inséré. Cela protège
  les personnalisations existantes, mais limite la marge de transformation.

---

## 5. Vérifications

### Installation sur base neuve — six modules, six bases

Pour chaque thème :

```
dropdb --if-exists themetest
python3 odoo19/odoo-bin -c odoo.conf -d themetest -i website,<theme> --without-demo=all \
    --stop-after-init --log-level=warn 2>&1 | grep -E "ERROR|CRITICAL|ParseError|Traceback" -A5 | head -20
```

**Résultat : aucune sortie pour les six modules** — aucune erreur, aucun warning
de vue. Puis application du thème, rendu des pages et compilation réelle du SCSS :

| Thème | Pages testées | Bundle `web.assets_frontend` | SCSS |
| --- | --- | --- | --- |
| `theme_presse_lite` | `/`, `/magazine`, `/blog` | 820 320 o | OK |
| `theme_presse` | + `/rubrique-economie`, `/auteur-camille-ferrand` | 824 989 o | OK |
| `theme_voyage_lite` | `/`, `/nos-voyages` | 800 739 o | OK |
| `theme_voyage` | + `/destination-vantour`, `/itineraire-cretes-de-vantour` | 806 161 o | OK |
| `theme_animalerie_lite` | `/`, `/notre-boutique`, `/shop` | 989 512 o | OK |
| `theme_animalerie` | + `/categorie-chiens` | 995 500 o | OK |

Toutes les pages répondent en HTTP 200.

**Point de méthode à retenir : une erreur SCSS ne remonte pas dans les logs
Odoo.** Le serveur sert silencieusement un bundle de repli de 12 ko contenant
`## CSS error message ##`. Trois erreurs ont été trouvées uniquement par ce
biais : `$o-theme-font-configs` indéfini (fichier de variables placé en
`prepend`), `Incompatible units: 'rem' and 'px'`, `Incompatible units: 'vw' and
'rem'` (le `clamp()` et le `min()` évalués par libsass). Le script
`scripts/check_theme.sh` télécharge le bundle et cherche cette chaîne.

### Contrôle statique

`bash scripts/lint.sh` → **`lint.sh : OK`** pour les six modules (manifeste,
licence et prix cohérents, fichiers obligatoires, extensions autorisées dans
`static/description`, XML bien formé, absence de `<tree>`, absence de la marque
interdite).

### Non-régression des six modules existants — impossible

`ai_document_extract`, `dougs_bridge`, `odoo_mcp_server`,
`amazon_connector_community`, `studio_lite`, `blog_social_publish` n'existent
plus : leur code a disparu avec le conteneur précédent et ne se trouve pas sur le
Drive. **La ligne « 0 failed, 0 error(s) of 91 tests » ne peut pas être
produite.** À la place, les six thèmes ont été installés **ensemble sur une même
base** (`website`, `website_blog`, `website_sale` + les six thèmes) sans erreur,
ce qui vérifie au moins l'absence de conflit entre eux.

### Nettoyage

Bases de test supprimées, `__pycache__` supprimés (6 dossiers).

---


### Ajouts postérieurs à la première livraison

- **Entrées de menu de site** — chaque thème déclare ses pages de démonstration
  dans le menu principal via `theme.website.menu`, comme `theme_dyonysos`.
- **Mode sombre sur les trois thèmes pro** — inversion complète des couleurs,
  activable par le bloc « Bascule mode sombre » à poser dans la page, ou
  automatiquement via la classe `o_<prefixe>_dark_auto` sur `<html>` (préférence
  système). Le choix est mémorisé dans le navigateur, sans appel réseau, et le
  script reste inerte dans l'éditeur. Contrastes du thème sombre vérifiés :

  | Thème | Texte | Texte secondaire | Accent |
  | --- | --- | --- | --- |
  | Presse | 15,94:1 | 8,78:1 | 5,59:1 |
  | Voyage | 15,59:1 | 8,72:1 | 6,35:1 |
  | Animalerie | 13,69:1 | 8,21:1 | 8,01:1 |

  Limite : le mode sombre assombrit les images de démonstration par un filtre CSS
  (`brightness(.88)`), il ne fournit pas de visuels alternatifs.

- **Variantes de mise en page sur les trois thèmes pro** — trois dispositions
  d'en-tête (centrée, avec bandeau d'information, minimale) et deux de pied de
  page (étendue à quatre colonnes, compacte). Elles s'ajoutent aux listes
  natives des panneaux « En-tête » et « Pied de page » de l'éditeur, avec un
  aperçu par variante, via `website.website_builder_assets` — même mécanique que
  `theme_dyonysos` (`BuilderSelectItem` pour l'en-tête, plugin
  `footer_templates_providers` pour le pied).

  Point technique à connaître : ces variantes remplacent `//header//nav` de
  `website.layout`, exactement comme `website.template_header_default`. **Elles
  sont donc mutuellement exclusives avec lui** — activer une variante sans
  désactiver le modèle natif produit une erreur `Element '<xpath
  expr="//header//nav">' cannot be located in parent view`. L'éditeur s'en charge
  automatiquement (`websiteConfig`) ; il faut y penser si l'on active une vue à
  la main ou par script de déploiement.

## 6. Propriété intellectuelle

- Aucun thème existant n'a été copié, adapté ni « légèrement modifié ». Les
  sources d'Odoo n'ont été lues que pour comprendre la structure attendue
  (`website/views/snippets/`, `website/static/src/scss/primary_variables.scss`,
  `odoo/tools/convert.py`, `website_blog`, `website_sale`).
- **Aucune image n'a été téléchargée.** Tous les visuels — images de
  démonstration, vignettes de blocs, icônes, maquettes de fiche — sont générés
  par programme avec Pillow : dégradés, formes géométriques, motifs abstraits,
  compositions typographiques. Les scripts sont dans `scripts/make_assets.py` et
  `scripts/make_mockups.py`, ils sont rejouables.
- Les polices utilisées dans les maquettes sont libres (Lora, Poppins, Carlito,
  Liberation). Les polices du thème (Playfair Display, Inter, Poppins, Nunito)
  sont chargées par Odoo depuis Google Fonts, comme pour tout thème Odoo.
- Aucun contenu de démonstration ne cite d'entreprise, de marque ou de personne
  réelle. Le thème animalerie ne contient aucune trace de « Pet Stone ».

---

## 7. Deux points à revoir avant publication

1. **Le texte OPL-1.** Le fichier `LICENSE` des trois modules payants devait être
   copié depuis `odoo_mcp_server/`, qui n'existe plus. Il a été rédigé d'après le
   texte canonique de l'Odoo Proprietary License v1.0 ; il faut le comparer
   caractère par caractère avec la version officielle avant de publier.
2. **La langue source.** Les gabarits sont écrits en français : le `.pot` exporté
   contient donc des chaînes sources françaises, et `i18n/fr.po` reprend le
   modèle à l'identique (100 % « traduit », par construction). Si tu vises
   l'Apps Store international, il faut basculer les sources en anglais et faire
   du français une vraie traduction — c'est une reprise de tous les gabarits.

---

## 8. Recommandations

- **Publier d'abord les gratuits, seuls, pendant deux à trois semaines.** Ils
  portent les téléchargements et les avis. Sortir les payants ensuite, quand la
  fiche gratuite affiche déjà un compteur.
- **`theme_presse` est le produit à pousser.** Il n'a pas d'équivalent sur
  l'Apps Store et le besoin est réel pour tout site Odoo qui publie. Les deux
  autres sont des marchés plus encombrés.
- **Le prix de 179,10 € du thème voyage détonne** au milieu de deux thèmes à
  345 €, et un prix non rond sur l'Apps Store fait « remise » plutôt que
  « positionnement ». Soit 179 €, soit 245 € si le contenu le justifie.
- **Prévoir une version dynamique du bloc « une ».** C'est la limite que les
  acheteurs remonteront en premier sur le thème presse : un petit modèle Python
  lisant `blog.post` transformerait le bloc statique en vrai bloc de une. C'est
  la principale évolution à budgéter.
- **Tester le tunnel de commande à chaque version mineure d'Odoo.** L'habillage
  de `website_sale` repose sur des sélecteurs de vues qui bougent.
- **Ne pas livrer les données de démonstration dans la version payante.** Aujourd'hui
  elles arrivent par la dépendance au module gratuit ; un acheteur qui installe
  sur sa base de production se retrouve avec douze produits fictifs. Une option
  de désactivation, ou un passage en clé `demo`, éviterait les tickets de support.
- **Sauvegarder le dépôt hors du conteneur.** Cette mission a commencé par la
  perte complète d'un environnement de travail. Un dépôt Git distant (même privé)
  coûte dix minutes et aurait évité de repartir de zéro.

---

*DYONYSOS — welcome@dyonysos.fr — https://dyonysos.fr*
