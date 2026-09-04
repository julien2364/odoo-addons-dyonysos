#!/usr/bin/env bash
# Démarre le serveur sur la base indiquée, appelle quelques pages et vérifie
# que le bundle SCSS du frontend compile réellement.
DB="${1:-themetest}"; shift
PAGES=("$@"); [ ${#PAGES[@]} -eq 0 ] && PAGES=("/" "/magazine")
cd /home/claude
LOG=/tmp/srv_$DB.log
python3 odoo19/odoo-bin -c odoo.conf -d $DB --http-port=8069 --log-level=warn > $LOG 2>&1 &
SRV=$!
for i in $(seq 1 60); do
  curl -s -o /dev/null http://127.0.0.1:8069/web/login && break
  sleep 2
done
RC=0
for p in "${PAGES[@]}"; do
  CODE=$(curl -s -o /tmp/page.html -w "%{http_code}" "http://127.0.0.1:8069$p")
  SIZE=$(wc -c < /tmp/page.html)
  echo "  $p -> HTTP $CODE (${SIZE} o)"
  [ "$CODE" != "200" ] && RC=1
done
curl -s -o /tmp/home.html http://127.0.0.1:8069/
CSS=$(grep -oE '/web/assets/[^"]*web\.assets_frontend[^"]*\.css' /tmp/home.html | head -1)
if [ -n "$CSS" ]; then
  CODE=$(curl -s -o /tmp/bundle.css -w "%{http_code}" "http://127.0.0.1:8069$CSS")
  SIZE=$(wc -c < /tmp/bundle.css)
  echo "  bundle assets_frontend -> HTTP $CODE (${SIZE} o)"
  if [ "$CODE" != "200" ]; then RC=1; fi
  # Une erreur SCSS ne remonte PAS dans les logs : Odoo sert un bundle de repli
  # qui contient un message d'erreur. C'est le seul moyen fiable de la voir.
  if grep -q "CSS error message\|css_error_message" /tmp/bundle.css; then
    echo "  ✗ ERREUR SCSS dans le bundle :"
    grep -o 'content: "Error:[^"]*"' /tmp/bundle.css | head -1 | cut -c1-400
    RC=1
  else
    echo "  ✓ SCSS compilé sans erreur"
  fi
else
  echo "  bundle assets_frontend introuvable dans le HTML"; RC=1
fi
kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
echo "  --- erreurs serveur ---"
grep -E "ERROR|CRITICAL|Traceback|CompileError|SassError" $LOG | grep -v "security risk" | head -15
exit $RC
