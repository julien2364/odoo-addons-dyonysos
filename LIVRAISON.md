# Livraison — 5 modules Odoo 19 DYONYSOS

Dépôt : `julien2364/odoo-addons-dyonysos`, branche `19.0`.
Version de tous les modules : `19.0.1.0.0`. Licence `OPL-1`, prix `250 € / module`.
Auteur `DYONYSOS`, support `welcome@dyonysos.fr`, site `https://dyonysos.fr`.

---

## 1. Ce qui est livré

| Module technique | Ce qu'il fait | Tests | `depends` Odoo | `external_dependencies` Python |
|---|---|---|---|---|
| `ai_document_extract` | Lit les PDF/images de factures fournisseurs et de notes de frais avec un modèle de vision et remplit le brouillon Odoo | 7 | `account`, `hr_expense` | `requests` (+ `pypdf`, optionnel, utilisé pour extraire la couche texte d'un PDF quand le fournisseur est OpenAI-compatible) |
| `dougs_bridge` | Constitue un lot des pièces validées (PDF + Factur-X + `journal.csv`) et le transmet au cabinet par API First, email, SFTP, dossier serveur ou ZIP | 10 | `account`, `hr_expense`, `account_edi_ubl_cii`, `mail` | `requests` (+ `paramiko` si transport SFTP) |
| `odoo_mcp_server` | Sert un endpoint MCP `/mcp` (JSON-RPC 2.0, Streamable HTTP) authentifié par clé API Odoo de scope `odoo.mcp`, avec liste blanche de modèles et journal d'audit | 20 | `base`, `base_setup` | aucune |
| `amazon_connector_community` | Importe les commandes Amazon SP-API en commandes de vente, remonte le suivi, pousse stock et prix | 15 | `sale_management`, `stock`, `delivery` | `requests` |
| `studio_lite` | Crée des champs `x_...` + la vue héritée qui les affiche, retouche les vues et crée des automatisations, le tout tracé et réversible | 20 | `base`, `web`, `mail`, `base_automation` | aucune |

**Total : 72 tests.** `odoo_mcp_server` et `studio_lite` sont déclarés `application: True` (icône dans le menu principal) ; les trois autres sont des extensions.

> Le tableau du `README.md` annonce encore 65 tests et une ventilation obsolète (`dougs_bridge` 8, `odoo_mcp_server` 15). Les chiffres ci-dessus sont ceux comptés dans les fichiers `tests/`. À corriger dans le README avant publication.

Chaîne CI (`.github/workflows/ci.yml`) : `lint` (manifestes, syntaxe Python, XML bien formé, présence de `static/description/icon.png` et `index.html`) → `tests` (clone de la pointe de `odoo/odoo` branche `19.0`, PostgreSQL 16, installation des 5 modules avec `--test-enable`) → `build` (`scripts/build.sh`, un zip par module + un bundle, artefacts 30 jours) → `release` sur tag `v*`. Déclencheurs : push et PR sur `19.0`, cron nocturne `17 3 * * *` UTC, et `workflow_dispatch`.

---

## 2. Mise en route, module par module

### 2.1 `ai_document_extract`

**À obtenir de l'extérieur** : une clé API chez l'un des fournisseurs suivants.

| Fournisseur | Valeur du champ « AI Provider » | Base URL à saisir | Modèle par défaut si champ vide |
|---|---|---|---|
| Anthropic | `Anthropic (Claude) — reads PDF natively` | vide | `claude-sonnet-4-5` |
| OpenAI | `OpenAI-compatible API` | vide | `gpt-4.1-mini` |
| Mistral | `OpenAI-compatible API` | `https://api.mistral.ai/v1` | à saisir |
| xAI Grok | `OpenAI-compatible API` | `https://api.x.ai/v1` | à saisir |
| Ollama local | `OpenAI-compatible API` | `http://localhost:11434/v1` | à saisir |

**Écrans**

1. Réglages › Comptabilité, bloc **« AI Digitization »** (inséré juste après le bloc « Factures fournisseurs »).
2. Setting « AI provider » : renseigner `AI Provider`, `AI API Key` (champ masqué), `AI Model` (laisser vide = défaut du fournisseur), `API Base URL` (laisser vide = défaut).
3. Setting « Automatic digitization » : trois cases, toutes cochées par défaut —
   `Digitize vendor bills automatically`, `Digitize expense receipts automatically`, `Create unknown suppliers`.
4. Enregistrer.

Les clés sont stockées dans `ir.config_parameter` : `ai_document_extract.provider`, `.api_key`, `.model`, `.base_url`, `.auto_invoices`, `.auto_expenses`, `.create_partner`.

**Premier test**

- Comptabilité › Fournisseurs › Factures : créer une facture fournisseur brouillon, y attacher un PDF de facture, cliquer le bouton **`AI Extract`** dans le bandeau (visible seulement si `state = draft` et type `in_invoice`/`in_refund`/`in_receipt`).
- Le fournisseur, le numéro, les dates, la devise et les lignes doivent se remplir ; le champ `AI Extract State` et le pourcentage de confiance apparaissent à côté de la référence.
- Vérifier l'entrée correspondante dans **Comptabilité › (menu d'audit `account.account_audit_menu`) › AI Extraction Log** : durée, jetons d'entrée/sortie, statut, et l'onglet « Extracted data » avec le JSON brut.
- Si le total extrait diffère du total recalculé, une note est postée dans le chatter de la facture — c'est le comportement attendu, pas une erreur.

Le mode automatique passe par `_get_edi_decoder` : tout PDF/image arrivant sur un journal d'achat (alias mail, glisser-déposer, upload) déclenche l'extraction sans bouton.

---

### 2.2 `dougs_bridge`

**À obtenir de l'extérieur**, selon le canal retenu :

- **API First** : URL de base et clé API (jeton Bearer) auprès de Dougs. Les chemins sont paramétrables, valeurs par défaut `/v1/invoices/outgoing`, `/v1/invoices/incoming`, `/v1/receipts`, champ multipart `file`.
- **Email** : l'adresse de collecte du cabinet.
- **SFTP** : hôte, port, utilisateur, mot de passe, chemin — et `pip install paramiko` dans l'image Odoo.
- **Dossier partagé** : un répertoire existant sur le serveur Odoo (montage Drive/Nextcloud synchronisé).
- **Téléchargement** : rien à obtenir, le ZIP reste attaché au lot.

**Écrans**

1. Réglages › Comptabilité, bloc **« Dougs Bridge — Accountant export »**.
2. Setting « Transport » : choisir `Transport`. Les champs affichés changent selon le choix (email / dossier / SFTP / API First). Renseigner aussi `Report email` — l'adresse qui reçoit le compte-rendu après chaque lot.
3. Setting « What to send » : `Customer invoices & credit notes`, `Vendor bills & credit notes`, `Approved expenses`, `Add Factur-X XML for customer invoices` (les quatre cochés par défaut), et `Days before a document is exported` (délai de grâce, `0` par défaut).
4. Enregistrer.

**Premier test**

- Comptabilité › Écritures comptables › **Accountant exports** : créer un lot.
- Bouton **`Collect documents`** : le lot se remplit avec les pièces validées de la période (`date_from` / `date_to`), avec les compteurs `count_out` / `count_in` / `count_expense`.
- Bouton **`Download ZIP`** d'abord : ouvrir l'archive et vérifier la présence des PDF, des `*_facturx.xml` pour les factures clients, et de `journal.csv` (séparateur `;`, UTF‑8 avec BOM, fins de ligne CRLF).
- Puis bouton **`Send to accountant`**. L'état passe à `sent` / `partial` / `error` ; l'onglet « Log » détaille le transport, chaque ligne porte son propre statut et son `remote_id` côté cabinet.
- En cas d'échec partiel : bouton **`Retry errors`**, qui ne rejoue que les lignes en erreur.

Envoi unitaire possible depuis une facture (`Send to accountant` dans le bandeau, visible si `state = posted` et `dougs_state != sent`), depuis une note de frais approuvée, ou en masse par l'action de liste **« Send to accountant (Dougs Bridge) »**.

---

### 2.3 `odoo_mcp_server`

**Rien à obtenir de l'extérieur** : ni compte, ni clé tierce. La clé est une clé API Odoo native.

**a. Activer le serveur**

Réglages › Paramètres généraux › **Intégrations**, setting « MCP Server (AI assistants) » :

| Champ | Clé `ir.config_parameter` | Défaut |
|---|---|---|
| Enable the MCP endpoint | `odoo_mcp_server.enabled` | `True` |
| Allow write operations | `odoo_mcp_server.allow_writes` | **`False`** |
| Log call arguments | `odoo_mcp_server.log_arguments` | `True` |
| Log retention (days) | `odoo_mcp_server.log_retention_days` | `90` |
| Max calls per minute and per key | `odoo_mcp_server.rate_limit` | `120` |

Endpoint désactivé ⇒ `/mcp` répond HTTP 503.

**b. Créer l'utilisateur porteur de la clé**

Créer un utilisateur dédié (ne pas utiliser un compte administrateur : la clé hérite exactement de ses droits) et lui donner le groupe **MCP User** (`odoo_mcp_server.group_mcp_user`) plus les groupes métier correspondant à ce que l'assistant doit voir. Le groupe **MCP Administrator** (`group_mcp_manager`) est réservé à qui configure la liste blanche et lit tout le journal.

**c. Créer la clé de scope `odoo.mcp`**

Le module ajoute un onglet **« MCP keys »** sur la fiche utilisateur (rappel de la procédure + compteur de clés) et une méthode `res.users.action_mcp_new_key()` qui ouvre l'assistant natif avec le scope pré-rempli — **mais aucun bouton de vue n'appelle cette méthode dans la version livrée**. La méthode fiable aujourd'hui est le shell Odoo :

```bash
cd ~/infra/odoo
docker compose run --rm --no-deps -T odoo odoo shell -d dyonysos --no-http <<'PY'
user = env['res.users'].search([('login', '=', 'mcp@dyonysos.fr')], limit=1)
key = env['res.users.apikeys'].with_user(user).sudo()._generate('odoo.mcp', 'Claude Desktop', False)
print(key)
env.cr.commit()
PY
```

Le troisième argument est la date d'expiration (`False` = pas d'expiration ; mettre une date est préférable). La clé n'est affichée qu'une fois : la copier immédiatement. Une clé se révoque depuis Préférences › Sécurité du compte de l'utilisateur.

**d. Ouvrir des modèles**

MCP Server › **Exposed models**. Trois modèles sont pré-chargés en lecture seule à l'installation : `res.partner`, `res.users` (champs limités à `id,name,login,active,company_id,share`) et `res.company`. **Rien d'autre n'est accessible tant qu'il n'est pas ajouté ici.**

Par modèle : `allow_read` / `allow_create` / `allow_write` / `allow_unlink`, un `domain` de restriction ANDé à toutes les recherches, un `field_names` (liste blanche de champs, vide = tous les champs lisibles par l'utilisateur), un `method_names` (méthodes autorisées via `odoo_call_method`, en plus de la liste sûre globale `name_search, default_get, fields_get, action_post, action_confirm, action_done, action_cancel, button_confirm, button_validate, message_post`), et `limit_default` / `limit_max` (50 / 500).

**e. Configuration du client MCP**

```json
{
  "mcpServers": {
    "odoo": {
      "type": "http",
      "url": "https://odoo.dyonysos.fr/mcp",
      "headers": {
        "Authorization": "Bearer VOTRE_CLE_ODOO_MCP"
      }
    }
  }
}
```

Emplacements du fichier : Claude Desktop `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) ou `%APPDATA%\Claude\claude_desktop_config.json` (Windows) ; Claude Code `.mcp.json` à la racine du projet ; Cursor `~/.cursor/mcp.json`. L'en-tête `X-Api-Key: <clé>` est accepté en variante de `Authorization: Bearer`.

**Premier test — sans client, en ligne de commande** :

```bash
curl -s https://odoo.dyonysos.fr/mcp \
  -H "Authorization: Bearer VOTRE_CLE_ODOO_MCP" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"odoo_list_models","arguments":{}}}'
```

Réponse attendue : la liste des modèles exposés. Une clé absente ou de mauvais scope renvoie HTTP 401 avec `WWW-Authenticate: Bearer realm="odoo-mcp"`.

Puis, dans le client : demander « liste-moi 5 contacts ». Vérifier ensuite **MCP Server › Access log** : outil appelé, modèle, ids touchés, durée, adresse IP, erreur éventuelle. Les arguments sont journalisés avec masquage automatique de tout ce qui ressemble à un secret (`password`, `token`, `api_key`, `iban`, `authorization`…).

Outils exposés : `odoo_list_models`, `odoo_model_fields`, `odoo_search`, `odoo_read`, `odoo_count`, `odoo_read_group`, `odoo_search_partners`, et — uniquement si `allow_writes` est activé — `odoo_create`, `odoo_write`, `odoo_unlink`, `odoo_call_method`.

---

### 2.4 `amazon_connector_community`

**À obtenir de l'extérieur** : une application SP-API chez Amazon.

1. Seller Central › Paramètres › **Autorisations utilisateur** › Développeur d'applications : demander le statut développeur si ce n'est pas déjà fait (validation Amazon, plusieurs jours).
2. **Developer Central** › Add new app client : créer une application de type *SP-API*, rôles minimaux — `Orders`, `Listings`, `Inventory`, `Product Listing`. Récupérer le **LWA Client ID** et le **LWA Client Secret**.
3. Autoriser l'application sur son propre compte vendeur (*Authorize* / self-authorization) pour obtenir le **Refresh Token LWA**.
4. Noter le **Seller ID** (Seller Central › Paramètres › Informations sur le compte).

**Écrans**

1. Ventes › **Amazon** › **Comptes Amazon** › Nouveau.
2. Groupe « Identifiants SP-API » : `Seller ID`, `LWA Client ID`, `LWA Client Secret`, `Refresh Token LWA` (les trois derniers visibles du seul groupe `base.group_system`), `Région` (`Europe` par défaut). L'`Endpoint` se calcule depuis la région et n'est modifiable que par un administrateur système — le laisser tel quel hors bac à sable.
3. Groupe « Paramétrage Odoo » : `Journal de vente`, `Équipe commerciale`, `Entrepôt`, `Liste de prix` (celle publiée vers Amazon), `Article frais de port` (un article de type service ; un article par défaut `product_amazon_shipping` est fourni), `Position fiscale`.
4. Groupe « Import » : `Confirmer automatiquement` (décoché par défaut), `Antériorité (jours)` (3 par défaut, fenêtre de la toute première synchronisation).
5. Onglet **Places de marché** : sélectionner celles à interroger. Dix sont pré-chargées : FR, DE, ES, IT, NL, BE, SE, PL, IE, UK.
6. Sur les articles à synchroniser : cocher `amazon_sync` (fiche article, groupe général) et renseigner `amazon_sku` sur la variante si le SKU vendeur diffère de la référence interne.

**Premier test**

- Bouton **`Tester la connexion`** sur la fiche compte : il appelle `/sellers/v1/marketplaceParticipations`. Il doit répondre sans erreur — c'est le contrôle des quatre identifiants.
- Bouton **`Importer les commandes`** : les commandes deviennent des `sale.order` avec `amazon_order_ref`, le client et l'adresse de livraison, les lignes rapprochées par SKU, et une ligne distincte pour les frais de port. L'import est idempotent : une commande déjà importée est ignorée.
- Vérifier **Ventes › Amazon › Journal de synchronisation** : opération, place de marché, nombre d'éléments, durée, état, message. Une commande en erreur est journalisée individuellement et n'interrompt pas le lot (savepoint par commande).
- Bouton **`Envoyer stock et prix`** puis **`Envoyer le suivi`** (ce dernier après avoir validé un bon de livraison portant un numéro de suivi).

---

### 2.5 `studio_lite`

**Rien à obtenir de l'extérieur.** Le groupe **Designer** (`studio_lite.group_studio_designer`) implique `base.group_system` et est attribué à l'administrateur à l'installation.

**Écrans** — menu racine **Studio Lite** :

- **Studio Lite › Créer › Nouveau champ** : `Modèle`, `Libellé du champ` (le `Nom technique` `x_...` s'en déduit), `Type` (14 types : char, text, integer, float, monetary, boolean, date, datetime, selection, many2one, one2many, many2many, html, binary), options selon le type (`Modèle lié`, `Champ inverse`, valeurs de sélection ligne à ligne), `Info-bulle`, `Obligatoire`, `Copié lors d'une duplication`, `Suivi au chatter`, puis le placement : `Vue cible` et position (après un champ existant, dans un onglet, ou en fin de formulaire).
- **Studio Lite › Créer › Nouvelle automatisation** : déclencheur (`Un enregistrement est créé`, `… est modifié`, `Un champ change de valeur`, `Une condition devient vraie`) et action (`Envoyer un email`, `Mettre à jour un champ`, `Créer une activité`, `Ajouter un abonné`). Les actions email / activité / abonné exigent un modèle doté d'un chatter, contrôlé à la création.
- **Studio Lite › Vues personnalisées** : masquer un champ, le rendre obligatoire ou en lecture seule (vue héritée `position="attributes"`).
- **Studio Lite › Personnalisations** : le journal de tout ce que le module a créé, désactivable puis supprimable dans l'ordre inverse de création.

**Premier test**

- Créer un champ `Numéro de dossier` de type char sur `res.partner`, placé après `Nom`, puis ouvrir un contact : le champ doit apparaître.
- Retourner dans **Personnalisations**, désactiver la ligne : le champ disparaît de la vue. La supprimer : le champ `x_numero_de_dossier` et la vue héritée disparaissent tous les deux.

Garde-fous vérifiés dans le code : le nom technique doit respecter `^x_[a-z0-9_]+$` ; un champ déjà existant est refusé ; le point d'ancrage est cherché dans la vue **avant** de générer l'héritage, et si l'ancrage est introuvable, rien n'est créé (le champ éventuellement créé est retiré) ; la suppression refuse tout champ qui ne commence pas par `x_` ou qui n'est pas un champ manuel.

---

## 3. Actions planifiées

Emplacement : Réglages › Technique › Automatisation › **Actions planifiées**.

| Module | Nom exact de l'action | Fréquence | État par défaut | Quand l'activer |
|---|---|---|---|---|
| `amazon_connector_community` | `Amazon Connector : import des commandes` | toutes les 10 min | **inactive** | Après un `Tester la connexion` puis un `Importer les commandes` manuels concluants |
| `amazon_connector_community` | `Amazon Connector : envoi du stock et des prix` | toutes les 15 min | **inactive** | Après un `Envoyer stock et prix` manuel accepté par Amazon sur au moins un SKU |
| `amazon_connector_community` | `Amazon Connector : remontée du suivi` | toutes les 30 min | **inactive** | Après un `Envoyer le suivi` manuel réussi sur un bon de livraison réel |
| `dougs_bridge` | `Dougs Bridge: export accounting documents` | 1 jour | **inactive** | Après un lot manuel `sent` sans erreur sur le transport retenu. Régler `Days before a document is exported` avant d'activer |
| `odoo_mcp_server` | `MCP Server: purge old access logs` | 1 semaine | **active** | Déjà active. Elle purge le journal d'audit au-delà de `odoo_mcp_server.log_retention_days` (90 jours) — la désactiver si le journal doit être conservé plus longtemps |

`ai_document_extract` et `studio_lite` ne livrent aucune action planifiée.

Les crons Amazon tournent **sur tous les comptes** (`self.search([])`) : ne pas les activer tant qu'un compte de test incomplet existe encore dans la base. Le cron `dougs_bridge` boucle sur **toutes les sociétés** et supprime le lot s'il est vide.

---

## 4. Publication sur apps.odoo.com

### Marche à suivre

1. **Compte** : se connecter sur `https://apps.odoo.com` avec le compte odoo.com DYONYSOS. Le nom d'éditeur affiché sera celui du compte — vérifier qu'il correspond à `DYONYSOS`.
2. **Déclarer le dépôt** : `https://apps.odoo.com/apps` › *My Repositories* (ou `https://www.odoo.com/my/repositories`) › Add a repository.
   - URL : `git@github.com:julien2364/odoo-addons-dyonysos.git`
   - Branche : `19.0`
3. **Clé de déploiement** : Odoo affiche une clé publique SSH. La coller dans GitHub › dépôt `odoo-addons-dyonysos` › *Settings › Deploy keys › Add deploy key*, **en lecture seule** (ne pas cocher « Allow write access »). Odoo clone ensuite la branche `19.0` périodiquement.
4. **Ce qu'Odoo lit dans le dépôt** : chaque répertoire de premier niveau contenant un `__manifest__.py` devient une app. Depuis le manifeste : `name`, `summary`, `description`, `version` (doit commencer par `19.0.`), `category`, `author`, `website`, `support`, `license` (`OPL-1` = module payant), `price` + `currency` (250.0 / EUR), `depends`, `external_dependencies`, `images`, `application`, `installable`.
5. **Visuels** : dans `<module>/static/description/` —
   - `icon.png` : icône affichée dans la liste des apps (présente pour les 5 modules) ;
   - `banner.png` : bandeau, déclaré via `images` dans chaque manifeste ;
   - `index.html` : la page de description longue rendue sur la fiche de l'app (présente pour les 5 modules) ;
   - captures d'écran complémentaires livrées : `ai_document_extract/screen_bills.png`, `amazon_connector_community/screen_orders.png` et `screen_sync.png`, `dougs_bridge/screen_batch.png`, `odoo_mcp_server/screen_log.png`, `studio_lite/screen_customizations.png` et `screen_field_wizard.png`.
6. **Validation** : la mise en ligne n'est **pas automatique**. Odoo effectue une revue manuelle de chaque module (conformité du manifeste, qualité de la description, absence de code interdit, licence cohérente avec le prix). Compter plusieurs jours ouvrés, et prévoir des allers-retours. Tant que la revue n'est pas passée, le module apparaît en attente et n'est pas achetable.
7. **Mises à jour** : incrémenter le dernier segment de `version` (`19.0.1.0.1`, …) et pousser sur `19.0`. Odoo repasse en revue les changements.

### Checklist avant de publier

- [ ] `./scripts/lint.sh` passe sans erreur en local et le job `lint` est vert sur `19.0`.
- [ ] Le job `tests` de la CI est vert (72 tests) — y compris le dernier run nocturne.
- [ ] `README.md` corrigé : 72 tests, et la ventilation par module alignée sur la section 1 de ce document.
- [ ] Les 5 `__manifest__.py` portent bien `version` en `19.0.x.y.z`, `license: OPL-1`, `price: 250.0`, `currency: EUR`, `author: DYONYSOS`, `support: welcome@dyonysos.fr`.
- [ ] Aucun `__pycache__`, `.pyc`, `.ruff_cache` ni fichier de travail dans les zips de `dist/` (`scripts/build.sh` les purge — vérifier après coup : `unzip -l dist/dougs_bridge-19.0.1.0.0.zip | grep -i cache`). **Les répertoires `.ruff_cache/` présents dans `dougs_bridge/` et `odoo_mcp_server/` doivent être supprimés du dépôt et ajoutés au `.gitignore` avant publication.**
- [ ] Chaque `index.html` relu : pas de promesse absente du code, mention explicite du périmètre non couvert (déjà présente pour `amazon_connector_community` et `studio_lite`).
- [ ] Les `banner.png` et `icon.png` s'affichent correctement (pas de transparence cassée, icône lisible en 128 px).
- [ ] Les fichiers de traduction `i18n/*.pot` et `i18n/fr.po` sont régénérés si des chaînes ont changé depuis la dernière passe.
- [ ] Clé de déploiement GitHub ajoutée **en lecture seule**.
- [ ] Un tag `v19.0.1.0.0` est poussé (déclenche le job `release` et attache les zips à la release GitHub).
- [ ] Les 5 modules s'installent sur une base Odoo 19 vierge depuis les zips de `dist/`, pas seulement depuis le dépôt.

---

## 5. Exploitation

Toutes les commandes ci-dessous depuis `~/infra/odoo` sur le VPS OVH.

### Sauvegarde avant mise à jour

```bash
cd ~/infra/odoo
mkdir -p ~/backups
STAMP=$(date +%Y%m%d-%H%M)
# Base de données
docker compose exec -T db pg_dump -U odoo -Fc dyonysos > ~/backups/dyonysos-$STAMP.dump
# Filestore (pièces jointes : PDF de factures, ZIP des lots Dougs)
docker compose exec -T odoo tar czf - /var/lib/odoo/filestore/dyonysos > ~/backups/filestore-$STAMP.tar.gz
ls -lh ~/backups/*$STAMP*
```

Restauration, si nécessaire :

```bash
docker compose stop odoo
docker compose exec -T db dropdb -U odoo dyonysos
docker compose exec -T db createdb -U odoo -O odoo dyonysos
docker compose exec -T db pg_restore -U odoo -d dyonysos < ~/backups/dyonysos-<STAMP>.dump
docker compose start odoo
```

### Mise à jour d'un module

```bash
cd ~/infra/odoo
git -C /chemin/vers/addons/odoo-addons-dyonysos pull        # ou déployer le nouveau zip
docker compose run --rm --no-deps -T odoo odoo -d dyonysos -u <module> --stop-after-init --no-http
docker compose restart odoo
```

`--no-deps` empêche le démarrage d'un second conteneur `db` ; `--stop-after-init` fait sortir le processus après la mise à jour ; `--no-http` évite le conflit de port avec l'instance en service. Plusieurs modules à la fois : `-u ai_document_extract,dougs_bridge`. Mise à jour de tout le lot : `-u ai_document_extract,dougs_bridge,odoo_mcp_server,amazon_connector_community,studio_lite`.

Première installation d'un module : remplacer `-u` par `-i`. Dépendances Python à ajouter dans l'image si besoin : `requests` (généralement déjà présent dans l'image officielle), `pypdf` (couche texte des PDF pour les fournisseurs OpenAI-compatibles), `paramiko` (transport SFTP de `dougs_bridge`).

### Où lire les journaux

| Quoi | Où |
|---|---|
| Extractions IA (durée, jetons, statut, JSON brut, erreur) | Comptabilité › menu d'audit › **AI Extraction Log** (`ai.extract.log`) |
| Lots envoyés au cabinet | Comptabilité › Écritures comptables › **Accountant exports** (`dougs.export.batch`), onglet « Log » + statut par ligne + chatter du lot |
| Appels MCP | **MCP Server › Access log** (`mcp.access.log`) : outil, modèle, ids, durée, IP, erreur, arguments (secrets masqués) |
| Synchronisations Amazon | Ventes › Amazon › **Journal de synchronisation** (`amazon.sync.log`) : compte, marketplace, opération, nombre d'éléments, durée, message |
| Personnalisations Studio Lite | **Studio Lite › Personnalisations** (`studio.customization`) et **Vues personnalisées** (`studio.view.customization`) |
| Serveur | `docker compose logs -f --tail=200 odoo` |

### Si un cron tourne en erreur

1. Réglages › Technique › Automatisation › Actions planifiées : ouvrir l'action. Odoo la **désactive automatiquement** après plusieurs échecs consécutifs — un cron « disparu » est en général un cron désactivé, pas un cron supprimé.
2. Lire l'erreur : `docker compose logs --tail=500 odoo | grep -i -A20 "<nom de l'action>"`.
3. Reproduire à la main : bouton correspondant sur la fiche (`Importer les commandes`, `Envoyer stock et prix`, `Envoyer le suivi`) ou lot Dougs manuel. Le journal métier du module (tableau ci-dessus) porte le message d'erreur exact, plus lisible que le log serveur.
4. Corriger la cause (clé expirée, marketplace non renseignée, dossier d'export inexistant, SMTP en échec), puis relancer manuellement avant de **réactiver** la case `active` du cron.
5. Le cron `Dougs Bridge: export accounting documents` crée un lot par société à chaque passage : si plusieurs lots vides s'accumulent, c'est que `action_collect` ne ramène rien — vérifier les trois cases « What to send » et le délai de grâce.

---

## 6. Limites connues et ce qui reste à faire

### `amazon_connector_community`

- **FBM uniquement.** Le module ne gère pas FBA (expéditions faites par Amazon), ni la facturation VCS, ni les retours et remboursements Amazon. C'est écrit dans la page de description du module, et cohérent avec le code : le push de stock écrit `fulfillment_channel_code: "DEFAULT"`, c'est-à-dire le stock marchand.
- **Pas de pagination.** `AmazonSpApi.get_orders()` accepte un paramètre `next_token`, mais `_import_orders()` ne l'utilise jamais : un seul appel `/orders/v0/orders` est fait par synchronisation. Au-delà de la taille de page renvoyée par Amazon (~100 commandes), le reliquat est perdu pour ce passage — il ne sera repris que si `LastUpdatedAfter` le recouvre encore au passage suivant, ce qui n'est pas garanti puisque `last_order_sync` est avancé à la fin. **À corriger avant d'exposer le module à un vendeur à fort volume.**
- **Stock et prix : une seule marketplace.** `_push_stock()` et `_push_price()` font `marketplace = self.marketplace_ids[:1]` — seule la première place de marché du compte reçoit les mises à jour, même si dix sont cochées. L'import de commandes, lui, interroge bien toutes les marketplaces.
- **`productType: "PRODUCT"` générique.** Les appels `PATCH /listings/2021-08-01/items/...` envoient un type de produit générique. Amazon peut refuser le patch pour certaines catégories qui exigent leur type réel — l'erreur remonte alors dans le journal de synchronisation.
- **Rapprochement par SKU seulement.** Une commande dont le `SellerSKU` n'a pas de correspondance dans Odoo lève une erreur sur cette commande ; le lot continue, mais la commande n'est pas importée.
- **Statut développeur Amazon.** L'obtention des rôles SP-API dépend d'une validation Amazon hors de notre contrôle, et les rôles « restricted » (données personnelles acheteur) font l'objet d'une revue supplémentaire.

### `dougs_bridge`

- **API First non vérifié contre la vraie API.** Dougs n'a pas publié de documentation publique d'API First. Les chemins (`/v1/invoices/outgoing`, `/v1/invoices/incoming`, `/v1/receipts`), le nom du champ multipart (`file`) et la forme des métadonnées sont **paramétrables précisément parce qu'ils sont des hypothèses**. Tant que Dougs n'a pas fourni sa spécification, le transport `apifirst` doit être considéré comme non validé en production. Les quatre autres transports ne dépendent d'aucun tiers.
- **SMTP en échec sur l'instance de Julien.** Le serveur sortant OVH répond `535` (échec d'authentification) sur `odoo.dyonysos.fr`. Conséquences directes : le transport **email** de `dougs_bridge` échoue, et le compte-rendu de lot (`Report email`) n'est jamais délivré. À corriger côté infrastructure (identifiants SMTP OVH, ou bascule vers un relais type Brevo/Postmark) avant de retenir le canal email. En attendant, utiliser `download`, `folder` ou `sftp`.
- **SFTP conditionné à `paramiko`.** Le paquet n'est pas dans `external_dependencies` du manifeste (seul `requests` y figure) : le transport lève une erreur explicite à l'exécution si `paramiko` manque. Ajouter `pip install paramiko` à l'image Docker si ce canal est retenu, ou ajouter `paramiko` aux dépendances déclarées.
- **Factur-X « best effort ».** L'échec de génération du XML Factur-X est capturé et journalisé, mais ne bloque pas l'envoi : le PDF part seul. Un correctif Community est livré (`account_edi_cii_fix.py`) parce que l'exportateur CII standard lit `deferred_start_date` / `deferred_end_date`, champs qui n'existent qu'avec la fonctionnalité de charges constatées d'avance d'Enterprise — sans ce correctif, l'export plante en Community.
- **Transport `folder` non transactionnel.** Les fichiers sont écrits directement dans le répertoire cible ; si la synchronisation Drive/Nextcloud est en retard ou en conflit, Odoo considère le lot comme envoyé.

### `odoo_mcp_server`

- **Pas de bouton pour créer une clé de scope `odoo.mcp`.** `res.users.action_mcp_new_key()` existe et pré-remplit le scope, mais aucune vue ne l'appelle : l'onglet « MCP keys » n'affiche qu'un rappel et un compteur. Aujourd'hui la clé se crée en shell (§ 2.3.c). **Ajouter le bouton est le correctif le plus rentable du lot** — sans lui, un acheteur ne saura pas créer sa clé.
- **Limitation de débit locale au worker.** `_RATE_BUCKET` est un dictionnaire en mémoire de processus. Avec plusieurs workers Odoo, la limite effective est `rate_limit × nombre de workers`, pas `rate_limit`. Acceptable comme garde-fou, insuffisant comme quota strict.
- **Transport HTTP simple, pas de SSE.** L'endpoint est un unique `POST /mcp` (JSON-RPC 2.0, y compris en lot). Les clients qui exigent un flux SSE ou une session `Mcp-Session-Id` persistante ne sont pas couverts.
- **`Access-Control-Allow-Origin: *`.** Le CORS est ouvert. Sans cookie de session (l'auth est par en-tête `Authorization`), il n'y a pas de vecteur CSRF, mais toute page web peut tenter un appel — la clé reste la seule barrière. À restreindre si l'endpoint devient public.
- **Corps de requête plafonné à 2 Mo**, `odoo_read` / `odoo_write` / `odoo_unlink` plafonnés à 1000 ids par appel.

### `ai_document_extract`

- **Périmètre plus étroit que Studio/Enterprise sur les PDF non-Anthropic.** Avec un fournisseur OpenAI-compatible, un PDF est réduit à sa couche texte via `pypdf` : un PDF scanné sans couche texte échoue avec un message explicite invitant à envoyer une image. Seul Anthropic reçoit le PDF nativement.
- **`pypdf` non déclaré** dans `external_dependencies` (seul `requests` y figure), alors que le chemin OpenAI + PDF en dépend. À déclarer ou à documenter dans l'`index.html`.
- **Types de fichiers acceptés** : PDF et `image/png`, `image/jpeg`, `image/jpg`, `image/webp`, `image/gif`. Tout autre type est refusé.
- **Coût à la charge de l'utilisateur.** Pas de crédits IAP, donc pas de garde-fou de budget : le journal d'extraction donne les jetons consommés a posteriori, mais rien ne plafonne le nombre d'appels. Une facture jointe deux fois est extraite deux fois.
- **Pas d'action planifiée de reprise.** Une extraction en erreur reste en erreur jusqu'à un clic manuel sur `AI Extract`.
- **Modèles par défaut figés dans le code** (`claude-sonnet-4-5`, `gpt-4.1-mini`) : ils vieilliront, d'où le champ `AI Model` laissé libre.

### `studio_lite`

Le module l'annonce lui-même dans sa page de description : **ce n'est pas Odoo Studio.** Ne sont pas couverts —

- l'édition visuelle par glisser-déposer ;
- la création de nouveaux modèles ou de nouvelles applications ;
- les rapports PDF (QWeb) ;
- les vues kanban sur mesure, les tableaux de bord, les vues pivot/graph personnalisées ;
- les circuits d'approbation.

Ce qui est couvert : la création de champs `x_...` (14 types) avec leur placement, trois retouches de vue (masquer / obligatoire / lecture seule), quatre types d'automatisation (email, mise à jour de champ, activité, abonné) sur quatre déclencheurs, et la réversibilité complète. Le groupe **Designer** implique `base.group_system` : dans les faits, seul un administrateur système peut utiliser le module.

### Transverse

- Le `README.md` annonce des chiffres de tests obsolètes (voir § 1).
- Les répertoires `.ruff_cache/` sont versionnés dans `dougs_bridge/` et `odoo_mcp_server/` : à supprimer et à ignorer.
- Aucun module n'a de script de migration : la première version publiée est `19.0.1.0.0`, donc rien à migrer aujourd'hui, mais toute évolution de schéma après mise en vente en exigera un.

---

## 7. Sécurité

| Module | Qui peut faire quoi | Où sont les secrets |
|---|---|---|
| `ai_document_extract` | Lecture du journal d'extraction : facturation (`account.group_account_invoice`) et approbateurs de notes de frais (`hr_expense.group_hr_expense_team_approver`). Écriture/suppression : `account.group_account_manager` seul. Le bouton `AI Extract` suit les droits standard sur la facture ou la note de frais. | Clé API dans `ir.config_parameter` (`ai_document_extract.api_key`), champ affiché en `password="True"`. Accessible à quiconque peut lire les paramètres système — c'est-à-dire aux administrateurs. |
| `dougs_bridge` | Pas de groupe dédié : les droits sont ceux de la comptabilité. Deux règles d'enregistrement globales multi-société sur `dougs.export.batch` et `dougs.export.line`. | Clé API First, mot de passe SFTP : `ir.config_parameter` (`dougs_bridge.apifirst_api_key`, `dougs_bridge.sftp_password`), champs `password="True"`. |
| `odoo_mcp_server` | Groupes **MCP User** (crée ses propres clés, lit son propre journal — règle `[('user_id','=',user.id)]`) et **MCP Administrator** (configure la liste blanche, lit tout le journal). Chaque appel MCP s'exécute avec l'environnement de l'utilisateur porteur de la clé : groupes, droits d'accès, règles d'enregistrement et multi-société d'Odoo s'appliquent intégralement, jamais de `sudo()`. | La clé API est un enregistrement `res.users.apikeys` (haché en base par Odoo, affiché une seule fois à la création, révocable, avec expiration facultative). Les arguments journalisés sont masqués sur tout mot-clé sensible. |
| `amazon_connector_community` | Groupes **Amazon : consultation** (implique `sales_team.group_sale_salesman`) et **Amazon : administration**. Règle globale multi-société sur `amazon.account.community`. | `lwa_client_id`, `lwa_client_secret`, `lwa_refresh_token` et `endpoint_url` portent `groups="base.group_system"` : ils ne sont ni lisibles ni modifiables hors administrateur système. `endpoint_url` est protégé délibérément — une URL détournée exfiltrerait le jeton d'accès Amazon. |
| `studio_lite` | Groupe unique **Designer**, qui implique `base.group_system`. Le module écrit dans `ir.model.fields`, `ir.ui.view` et `base.automation` : c'est un pouvoir d'administrateur, correctement borné à ce groupe. Les garde-fous (`^x_[a-z0-9_]+$`, refus de supprimer un champ non manuel, vérification de l'ancrage avant écriture) limitent les dégâts accidentels, pas les malveillants. | Aucun secret. |

### Les deux réglages à décider consciemment

**1. `odoo_mcp_server.allow_writes` — interrupteur global d'écriture MCP. Désactivé par défaut.**

Réglages › Paramètres généraux › Intégrations › « Allow write operations ». Tant qu'il est à `False`, les outils `odoo_create`, `odoo_write`, `odoo_unlink` et `odoo_call_method` ne sont **même pas listés** au client MCP, et sont refusés s'ils sont appelés — quelles que soient les cases `allow_create` / `allow_write` / `allow_unlink` cochées sur chaque modèle. C'est la seule barrière qui empêche un assistant de modifier la base sur une mauvaise interprétation d'une consigne. Recommandation : le laisser à `False`, et ne l'activer qu'après avoir (a) restreint la liste blanche aux seuls modèles concernés, (b) posé un `domain` de restriction sur chacun, (c) créé un utilisateur porteur de clé aux droits minimaux, et (d) vérifié le journal d'audit sur une semaine de lecture seule.

**2. `ai_document_extract.create_partner` — création automatique de fournisseurs par l'OCR. Activé par défaut.**

Réglages › Comptabilité › AI Digitization › « Create unknown suppliers ». Coché, l'extraction crée un `res.partner` quand elle ne retrouve pas le fournisseur par TVA, email ou nom. C'est ce qui rend la numérisation vraiment automatique — et c'est aussi ce qui pollue le carnet d'adresses avec des doublons quand le nom lu diffère d'un caractère, ou quand un modèle hallucine un nom. Décoché, une facture dont le fournisseur est inconnu reste sans partenaire, à compléter à la main. Recommandation pour DYONYSOS : le décocher pendant les premières semaines, contrôler la qualité des noms extraits dans le journal d'extraction, puis l'activer si le rapprochement s'avère fiable.

---

DYONYSOS — welcome@dyonysos.fr
