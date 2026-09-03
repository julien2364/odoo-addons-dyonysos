# Odoo addons DYONYSOS (Odoo 19)

| Module | Rôle | Tests |
|---|---|---|
| `ai_document_extract` | OCR IA des factures fournisseurs et notes de frais (Community) | 7 tests |
| `dougs_bridge` | Export des pièces comptables vers le cabinet (API First / email / SFTP / dossier / ZIP) | 8 tests |

## Installation (serveur odoo.dyonysos.fr)

1. Copier les dossiers dans le répertoire d'addons personnalisés monté dans le conteneur Odoo (ex. `~/infra/odoo/addons/`).
2. `pip install requests` est déjà satisfait par Odoo ; pour SFTP ajouter `paramiko` dans le Dockerfile.
3. Redémarrer Odoo puis Apps › Mettre à jour la liste › installer les deux modules
   (ou `odoo -d <db> -i ai_document_extract,dougs_bridge --stop-after-init`).

## Tests

```bash
odoo -c odoo.conf -d testdb -i ai_document_extract,dougs_bridge --test-enable --test-tags /ai_document_extract,/dougs_bridge --stop-after-init
```

## Publication Apps Store

Un dépôt GitHub par module (ou un dépôt avec un dossier par module), branche `19.0`, licence OPL-1, prix 250 € (`__manifest__.py`).
Les visuels sont dans `static/description/` (icon.png, banner.png, captures, index.html).
