#!/bin/bash
# Epic level 60 PvP armor overlay for 12785/12795. Usage: wov/pvp_epic_vendor.sh check|dryrun|apply|rollback
# apply/rollback take a backup of the affected vendor rows first and reload the vendor cache (no restart).
set -euo pipefail
cd /opt/wow/headless-dm; . ops/env.sh
SQL=wov/sql/pvp_epic_vendor_60.sql; UNDO=wov/sql/pvp_epic_vendor_60_rollback.sql
E="12784,12785,12794,12795"
check() {
  db acore_world -e "SELECT v.entry, COUNT(*) total, SUM(i.Quality=4) epic, SUM(i.Quality=3) rare,
    GROUP_CONCAT(DISTINCT v.ExtendedCost ORDER BY v.ExtendedCost) ext_cost, MAX(c.npcflag) npcflag
    FROM npc_vendor v JOIN item_template i ON i.entry=v.item JOIN creature_template c ON c.entry=v.entry
    WHERE v.entry IN ($E) GROUP BY v.entry;"
  db acore_world -N -e "SELECT IF(COUNT(*)=96,'OK: 96 epic overlay rows present',CONCAT('MISSING: ',96-COUNT(*),' of 96 overlay rows'))
    FROM npc_vendor WHERE entry IN (12785,12795) AND slot=1 AND ExtendedCost IN (2257,2289) AND ((item BETWEEN 16437 AND 16484) OR (item BETWEEN 16533 AND 16580) OR (item BETWEEN 17578 AND 17625));"
  db acore_world -N -e "SELECT IF(SUM(ExtendedCost IN (2403,2569))=42 AND MIN(c.npcflag & 128)=128,'OK: 42 weapons at 40000/60000, vendor flag set','NOT OK: weapons not (fully) applied')
    FROM npc_vendor v JOIN creature_template c ON c.entry=v.entry WHERE v.entry IN (12784,12794);"
}
backup() {
  B=/opt/wow/backups/pvp-epic-vendor-$(date +%Y%m%d-%H%M%S); mkdir -p "$B"
  MYSQL_PWD="$DB_PASS" mysqldump --default-character-set=utf8mb4 -h"${DB_HOST:-127.0.0.1}" -P"${DB_PORT:-3306}" -u"${DB_USER:-acore}" \
    --no-create-info --skip-extended-insert --replace acore_world npc_vendor --where="entry IN ($E)" > "$B/npc_vendor.sql"
  MYSQL_PWD="$DB_PASS" mysqldump --default-character-set=utf8mb4 -h"${DB_HOST:-127.0.0.1}" -P"${DB_PORT:-3306}" -u"${DB_USER:-acore}" \
    --no-create-info --skip-extended-insert --replace acore_world creature_template --where="entry IN ($E)" > "$B/creature_template.sql"
  check > "$B/check-before.txt"; echo "backup: $B"
}
case "${1:-check}" in
  check) check ;;
  dryrun) { echo "START TRANSACTION;"; cat "$SQL"; echo "SELECT entry, COUNT(*) rows_after, SUM(slot=1) overlay FROM npc_vendor WHERE entry IN (12785,12795) GROUP BY entry;"; echo "ROLLBACK;"; } | db acore_world -t ;;
  apply) backup; db acore_world < "$SQL"; ra "reload npc_vendor"; ra "reload creature_template 12784"; ra "reload creature_template 12794"; check ;;
  rollback) backup; db acore_world < "$UNDO"; ra "reload npc_vendor"; ra "reload creature_template 12784"; ra "reload creature_template 12794"; check ;;
  *) echo "usage: $0 check|dryrun|apply|rollback"; exit 2 ;;
esac
