#!/usr/bin/env bash
# Applique un thème au site de la base indiquée.
DB="$1"; THEME="$2"
cd /home/claude
cat > /tmp/_apply.py <<PY
mod = env['ir.module.module'].search([('name', '=', '$THEME')])
website = env['website'].search([], limit=1)
mod.with_context(website_id=website.id).button_choose_theme()
env.cr.commit()
print("APPLIED", website.theme_id.name)
PY
timeout 900 python3 odoo19/odoo-bin shell -c odoo.conf -d "$DB" --log-level=warn --no-http < /tmp/_apply.py 2>&1 | grep -E "APPLIED|Error|Traceback"
