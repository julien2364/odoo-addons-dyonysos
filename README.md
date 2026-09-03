# Odoo 19 addons — DYONYSOS

Cinq modules Odoo 19, compatibles **Community et Enterprise**, développés pour combler ce que
Community n'a pas et pour être vendus sur l'Odoo Apps Store (licence OPL-1, 250 € pièce).

| Module | Ce qu'il fait | Tests |
|---|---|---|
| `ai_document_extract` | Numérisation IA des factures fournisseurs et notes de frais (Claude, OpenAI, Mistral, Grok) — équivalent de l'OCR Enterprise, sans crédits IAP | 7 |
| `dougs_bridge` | Envoi des pièces comptables au cabinet (API First / email / SFTP / dossier partagé / ZIP), avec Factur-X et journal CSV | 8 |
| `odoo_mcp_server` | Serveur **MCP** natif : branche Claude, ChatGPT ou Cursor sur Odoo, avec clés API natives, liste blanche de modèles et journal d'audit | 15 |
| `amazon_connector_community` | Connecteur Amazon **SP-API** pour Community : commandes, suivi, stock, prix, 10 marketplaces UE | 15 |
| `studio_lite` | Équivalent léger de Studio : champs personnalisés, placement dans les vues, automatisations sans code, tout réversible | 20 |

**65 tests, tous verts** sur Odoo 19 (branche 19.0).

## Installation sur un serveur

```bash
unzip odoo-addons-dyonysos-all.zip -d /chemin/vers/addons
pip install requests            # + paramiko si vous utilisez le transport SFTP
odoo -d <base> -i ai_document_extract,dougs_bridge,odoo_mcp_server --stop-after-init
```

Sur l'instance DYONYSOS (Docker, VPS OVH) :

```bash
cd ~/infra/odoo
docker compose run --rm --no-deps -T odoo odoo -d dyonysos -i <modules> --stop-after-init --no-http
docker compose restart odoo
```

## Développement

```bash
./scripts/lint.sh                     # manifestes, syntaxe Python, XML, visuels Apps Store
./scripts/build.sh                    # un zip par module + un bundle, dans dist/
./scripts/build.sh studio_lite        # un seul module
```

Tests, sur une base Odoo 19 de travail :

```bash
odoo -c odoo.conf -d testdb --addons-path=<odoo>/addons,. \
     -i ai_document_extract,dougs_bridge,odoo_mcp_server,amazon_connector_community,studio_lite \
     --test-enable --test-tags /ai_document_extract,/dougs_bridge,/odoo_mcp_server,/amazon_connector_community,/studio_lite \
     --stop-after-init
```

## Intégration continue

`.github/workflows/ci.yml` : à chaque push et chaque PR sur `19.0`, plus **toutes les nuits à 03h17 UTC**
(la CI clone la pointe de la branche 19.0 d'Odoo : la tâche nocturne signale une régression venant
d'Odoo lui-même avant qu'un client ne la rencontre).

Trois étapes enchaînées : contrôles statiques → installation et tests sur PostgreSQL 16 → construction
des archives, publiées en artefacts pendant 30 jours. Un tag `v*` attache en plus les zips à la release
GitHub.

## Actions planifiées livrées dans les modules

| Module | Action planifiée | État par défaut |
|---|---|---|
| `dougs_bridge` | Export des pièces comptables vers le cabinet | inactive |
| `odoo_mcp_server` | Purge des journaux d'audit au-delà de la rétention | **active**, hebdomadaire |
| `amazon_connector_community` | Import des commandes (10 min), push stock et prix (15 min), remontée du suivi (30 min) | inactives |

Les actions inactives ne s'activent qu'une fois les clés d'API saisies et un premier essai manuel
concluant : Réglages › Technique › Automatisation › Actions planifiées.

## Publication sur l'Odoo Apps Store

Compte odoo.com › Mes dépôts : ajouter `git@github.com:julien2364/odoo-addons-dyonysos.git`,
branche `19.0`, et coller la clé de déploiement fournie par Odoo dans les réglages du dépôt GitHub.
Odoo lit ensuite les manifestes (prix, licence, description) et les visuels de
`static/description/` (`icon.png`, `banner.png`, `index.html`).

---

DYONYSOS — <welcome@dyonysos.fr> — https://dyonysos.fr
