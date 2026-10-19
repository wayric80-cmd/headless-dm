#!/usr/bin/env python3
"""Way of Vanilla: give random bots player-style names and rebuild the playerbots name pool.
Bots that have already talked with a real player keep their name (continuity).
RUN ONLY WITH wow-world STOPPED (the server caches character names).

  python3 wov/rename_bots.py plan  [--share 0.6]   show what would change
  python3 wov/rename_bots.py apply [--share 0.6]   rename + pool; mapping saved in table wov_rename (for revert)
  python3 wov/rename_bots.py revert                put the old names back (also with wow-world stopped)
Afterwards: python3 wov/gen_players.py project (BIO_ templates) and start wow-world.
"""
import argparse, os, random, re, subprocess, sys
HERE = os.path.dirname(os.path.realpath(__file__)); REPO = os.path.dirname(HERE)
NAMES = os.path.join(HERE, "names", "player-names.txt")
TEXTCOLS = ["backstory", "personality", "gist", "motivation", "motivation_short", "source", "craft", "craft_short", "kin", "kin_short"]

def db(sql, fetch=True):
    r = subprocess.run(["bash", "-c", ". ops/env.sh && db acore_characters -N --batch -e \"$Q\""], cwd=REPO,
                       env=dict(os.environ, Q=sql), capture_output=True, text=True)
    if r.returncode: sys.exit("SQL error: " + r.stderr)
    return [l.split("\t") for l in r.stdout.splitlines()] if fetch else None

def q(s): return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"

def world_running():
    return subprocess.run(["pgrep", "-x", "worldserver"], capture_output=True).returncode == 0

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["plan", "apply", "revert"])
    ap.add_argument("--share", type=float, default=0.6); a = ap.parse_args()
    if a.cmd != "plan" and world_running(): sys.exit("stop wow-world first")
    if a.cmd == "revert":
        rows = db("SELECT guid, old_name FROM wov_rename")
        for g, old in rows:
            db(f"UPDATE characters SET name={q(old)} WHERE guid={g}", False)
        print("reverted", len(rows)); return
    pool = [l.strip() for l in open(NAMES) if l.strip()]
    taken = {r[0].lower() for r in db("SELECT name FROM characters")}
    pool = [n for n in pool if n.lower() not in taken]
    random.seed(20261019); random.shuffle(pool)
    bots = db("SELECT c.guid, c.name FROM characters c JOIN acore_auth.account a ON a.id=c.account "
              "WHERE a.username LIKE 'RNDBOT%' AND c.guid NOT IN (SELECT guid FROM wov_rename) "
              "AND c.guid NOT IN (SELECT bot_guid FROM mod_ollama_chat_history) ORDER BY c.guid"
              ) if db("SHOW TABLES LIKE 'wov_rename'") else \
           db("SELECT c.guid, c.name FROM characters c JOIN acore_auth.account a ON a.id=c.account "
              "WHERE a.username LIKE 'RNDBOT%' AND c.guid NOT IN (SELECT bot_guid FROM mod_ollama_chat_history) ORDER BY c.guid")
    chosen = [b for b in bots if random.random() < a.share]
    plan = list(zip(chosen, pool))
    print(f"{len(bots)} bots, renaming {len(plan)}; pool left {len(pool) - len(plan)}")
    for (g, old), new in plan[:15]: print(f"  {old} -> {new}")
    if a.cmd == "plan": return
    db("CREATE TABLE IF NOT EXISTS wov_rename (guid INT UNSIGNED PRIMARY KEY, old_name VARCHAR(12) NOT NULL, "
       "new_name VARCHAR(12) NOT NULL, at DATETIME DEFAULT CURRENT_TIMESTAMP)", False)
    lore = {r[0]: r[1:] for r in db("SELECT guid, " + ", ".join(f"IFNULL({c},'')" for c in TEXTCOLS) + " FROM lore_character")}
    for (g, old), new in plan:
        db(f"INSERT INTO wov_rename (guid, old_name, new_name) VALUES ({g}, {q(old)}, {q(new)}); "
           f"UPDATE characters SET name={q(new)} WHERE guid={g};", False)
        if g in lore:
            vals = [re.sub(rf"\b{re.escape(old)}\b", new, v.replace("\\n", "\n")) for v in lore[g]]
            sets = ", ".join(f"{c}={q(v)}" for c, v in zip(TEXTCOLS, vals) if v)
            if sets: db(f"UPDATE lore_character SET {sets} WHERE guid={g}", False)
    print("renamed", len(plan))
    # name pool for bots created later: ~60 % player-style, the rest the old fantasy names
    left = pool[len(plan):]
    db("CREATE TABLE IF NOT EXISTS wov_names_backup LIKE playerbots_names", False)
    if not db("SELECT COUNT(*) FROM wov_names_backup")[0][0] != "0":
        db("INSERT INTO wov_names_backup SELECT * FROM playerbots_names", False)
    cats = [r[0] for r in db("SELECT DISTINCT gender FROM wov_names_backup")]
    db("DELETE FROM playerbots_names", False)
    nid = 1
    for c in cats:
        fant = [r[0] for r in db(f"SELECT name FROM wov_names_backup WHERE gender={c} ORDER BY RAND() LIMIT {int(len(left) * 0.66) + 1}")]
        rows = [(n, c) for n in set(fant) | set(left)]
        for i in range(0, len(rows), 500):
            chunk = rows[i:i + 500]
            db("INSERT IGNORE INTO playerbots_names (name_id, name, gender) VALUES " +
               ",".join(f"({nid + j}, {q(n)}, {g})" for j, (n, g) in enumerate(chunk)), False)
            nid += len(chunk)
    print("name pool rebuilt:", db("SELECT COUNT(*) FROM playerbots_names")[0][0], "rows")

if __name__ == "__main__":
    main()
