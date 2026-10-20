#!/usr/bin/env python3
"""Way of Vanilla: toxic players sometimes get reported.

Runs every 5 minutes (systemd user timer wov-reports.timer). Reads new bot lines from ledger_chat; a line with
name-calling has a chance of being "reported": the bot gets a GM mute (15-60 min, whole account, like a real
mute). Never a ban/suspension: playerbots crashes the worldserver when it tries to log in a banned bot.
Everything is logged in table wov_reports. Tuning below. Dry run: python3 wov/reports.py --dry-run
"""
import os, random, re, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
INSULT = re.compile(r"\b(noob\w*|n00b\w*|nubs?|idiots?|morons?|losers?|dumbass\w*|scrubs?|clowns?|l2p|stfu|rekt|"
                    r"trash|garbage|pathetic|bitch\w*|asshole\w*|asshat\w*|jackass\w*|shut up|retard\w*|tard)\b", re.I)
DIRECT = re.compile(r"\b(you|u|ur|youre|you're|ya)\b", re.I)
SWEAR = re.compile(r"\b(fuck\w*|shit\w*|wtf|ffs|damn\w*|crap\w*|piss\w*)\b", re.I)
P_INSULT, P_DIRECT, P_TO_REAL, P_SWEAR = 0.10, 0.20, 0.35, 0.02
DRY = "--dry-run" in sys.argv

def sh(cmd):
    return subprocess.run(["bash", "-c", ". ops/env.sh && " + cmd], cwd=REPO, capture_output=True, text=True)

def db(sql):
    r = sh('db acore_characters -N --batch -e "$Q"'.replace("$Q", sql.replace('"', '\\"')))
    if r.returncode: sys.exit(r.stderr)
    return [l.split("\t") for l in r.stdout.splitlines()]

def q(s): return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"

db("CREATE TABLE IF NOT EXISTS wov_reports (id INT AUTO_INCREMENT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP, "
   "guid INT UNSIGNED, name VARCHAR(24), action VARCHAR(16), minutes INT, text VARCHAR(512), KEY(guid))")
db("CREATE TABLE IF NOT EXISTS wov_reports_state (k VARCHAR(16) PRIMARY KEY, v BIGINT)")
# housekeeping: playerbots creates new bot accounts at WotLK level; this realm is Classic
r = sh("db acore_auth -e \"UPDATE account SET expansion=0 WHERE expansion<>0\"")
st = db("SELECT v FROM wov_reports_state WHERE k='last_id'")
if not st:
    last = db("SELECT IFNULL(MAX(id),0) FROM ledger_chat")[0][0]
    db(f"INSERT INTO wov_reports_state VALUES ('last_id', {last})"); print("initialised at", last); sys.exit()
last = int(st[0][0])
rows = db(f"SELECT l.id, l.speaker_guid, l.speaker_name, IFNULL(l.listener_guid,0), l.text, c.online, "
          f"IFNULL((SELECT 1 FROM characters c2 JOIN acore_auth.account a ON a.id=c2.account "
          f"WHERE c2.guid=l.listener_guid AND a.username NOT LIKE 'RNDBOT%'),0) "
          f"FROM ledger_chat l JOIN characters c ON c.guid=l.speaker_guid WHERE l.id>{last} AND l.speaker_is_bot=1 ORDER BY l.id")
done = set()
for rid, guid, name, listener, text, online, to_real in rows:
    last = max(last, int(rid))
    if guid in done or online != "1":
        continue
    p = 0.0
    if INSULT.search(text):
        p = P_TO_REAL if to_real == "1" else (P_DIRECT if DIRECT.search(text) else P_INSULT)
    elif SWEAR.search(text):
        p = P_SWEAR
    if not p or random.random() >= p:
        continue
    done.add(guid)
    minutes = random.choice([15, 20, 30, 30, 45, 60])
    action, cmd = "mute", f'mute {name} {minutes} Reported for abusive language'
    print(f"{action} {name} {minutes}m: {text[:80]}")
    if DRY:
        continue
    r = sh(f'ra "{cmd}"')
    db(f"INSERT INTO wov_reports (guid, name, action, minutes, text) VALUES ({guid}, {q(name)}, '{action}', {minutes}, {q(text[:500])})")
if not DRY:
    db(f"UPDATE wov_reports_state SET v={last} WHERE k='last_id'")
