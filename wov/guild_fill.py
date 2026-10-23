#!/usr/bin/env python3
"""Way of Vanilla: keep random bots in guilds like a real population.

Targets (share of random bots in a guild): level 40+ 90 %, 20-39 80 %, 10-19 70 %, 1-9 untouched.
Guild kinds per faction: leveling, pvp, pve, mixed (wov_guild_type). The bot's drive (wov_player.drive)
and level decide the kind. Guilds with a real player (any non-RNDBOT member, e.g. Horde Hub) are never
filled automatically. Selection is stable per character (hash), so the same bots stay "guildless".
Members are added through the GM console (.guild invite), so the server writes everything itself and the
ledger records guild_join as usual.

  python3 wov/guild_fill.py --dry-run         plan only
  python3 wov/guild_fill.py --max 60          create missing guilds, then invite at most 60 bots
"""
import argparse, os, re, socket, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TARGET = [(40, 90), (20, 80), (10, 70)]
ALLIANCE = {1, 3, 4, 7, 11}
# (faction, kind, name). Existing guilds are adopted by name.
PLAN = [
    ('H', 'pve', 'Titans of the Blood Sun'), ('H', 'pvp', 'Knights of the Sovereign'),
    ('H', 'leveling', 'Grind Till Dawn'), ('H', 'pve', 'Ashen Vanguard'), ('H', 'mixed', 'Smoke and Mirrors'),
    ('A', 'mixed', 'Disciples of the Light'), ('A', 'leveling', 'Late Night Levelers'), ('A', 'pvp', 'Southshore Survivors'),
    ('A', 'pve', 'Molten Ambition'), ('A', 'pve', 'Bad Medicine'), ('A', 'mixed', 'Hearth and Home'),
]

def db(sql):
    r = subprocess.run(['bash', '-c', '. ops/env.sh >/dev/null 2>&1 && db acore_characters -N --batch -e "$Q"'], cwd=REPO,
                       env=dict(os.environ, Q=sql), capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    return [l.split('\t') for l in r.stdout.splitlines() if l]

def ra_creds():
    r = subprocess.run(['bash', '-c', '. ops/env.sh >/dev/null 2>&1 && printf "%s\\n%s" "$RA_USER" "$RA_PASS"'], cwd=REPO,
                       capture_output=True, text=True)
    u, p = (r.stdout.split('\n') + ['', ''])[:2]
    if not u or not p:
        sys.exit('RA_USER/RA_PASS missing')
    return u, p

class RA:
    """Minimal AzerothCore remote console client (one session, many commands)."""
    def __init__(self):
        user, pw = ra_creds()
        for attempt in range(6):
            try:
                self.s = socket.create_connection(('127.0.0.1', 3443), timeout=10)
                break
            except OSError:
                time.sleep(5)
        else:
            sys.exit('RA console busy or down')
        self.read_until(b'Username:'); self.send(user)
        self.read_until(b'Password:'); self.send(pw)
        out = self.read_until(b'AC>')
        if b'AC>' not in out:
            sys.exit('RA login failed')
    def send(self, line):
        self.s.sendall(line.encode() + b'\r\n')
    def read_until(self, token, timeout=10):
        self.s.settimeout(timeout); buf = b''
        try:
            while token not in buf:
                chunk = self.s.recv(4096)
                if not chunk:
                    break
                buf += chunk
        except socket.timeout:
            pass
        return buf
    def cmd(self, line):
        self.send(line)
        return self.read_until(b'AC>').decode(errors='replace').replace('AC>', '').strip()
    def close(self):
        try:
            self.send('quit'); self.s.close()
        except OSError:
            pass

def stable(guid):
    return (int(guid) * 2654435761) % 4294967296 % 100

def target_pct(level):
    for lo, pct in TARGET:
        if level >= lo:
            return pct
    return 0

def kind_for(level, drive, guid):
    if level < 20:
        return 'leveling' if stable(guid * 7) < 85 else 'mixed'
    if drive == 'pvp':
        return 'pvp'
    if drive == 'dungeon':
        return 'pve' if level >= 30 else 'leveling'
    if drive == 'level':
        return 'pve' if level >= 50 else 'leveling'
    # drive pvp is rare: a third of the social/other bots 20+ join a PvP guild so those guilds are not empty
    return 'pvp' if stable(guid * 11) < 35 else 'mixed'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max', type=int, default=60)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    db("CREATE TABLE IF NOT EXISTS wov_guild_type (guildid INT UNSIGNED NOT NULL PRIMARY KEY, kind ENUM('leveling','pvp','pve','mixed') NOT NULL)")
    guilds = {r[1]: int(r[0]) for r in db('SELECT guildid, name FROM guild')}
    real = {int(r[0]) for r in db("SELECT DISTINCT m.guildid FROM guild_member m JOIN characters c ON c.guid=m.guid JOIN acore_auth.account x ON x.id=c.account WHERE x.username NOT LIKE 'RNDBOT%'")}
    chars = [dict(guid=int(g), name=n, level=int(l), faction='A' if int(r) in ALLIANCE else 'H', drive=d or '', online=o == '1', guild=int(gid) if gid not in ('NULL', '') else 0)
             for g, n, l, r, d, o, gid in db("SELECT c.guid, c.name, c.level, c.race, IFNULL(w.drive,''), c.online, IFNULL(m.guildid,'NULL') FROM characters c JOIN acore_auth.account x ON x.id=c.account AND x.username LIKE 'RNDBOT%' LEFT JOIN wov_player w ON w.guid=c.guid LEFT JOIN guild_member m ON m.guid=c.guid")]
    ra = None if a.dry_run else RA()
    # 1. create or adopt the planned guilds
    used_leaders = set()
    for fac, kind, name in PLAN:
        if name not in guilds:
            pref = [c for c in chars if c['faction'] == fac and c['online'] and not c['guild'] and c['level'] >= 30 and c['guid'] not in used_leaders]
            pref.sort(key=lambda c: (kind_for(c['level'], c['drive'], c['guid']) != kind, -c['level']))
            if not pref:
                print('no online leader for', name); continue
            leader = pref[0]; used_leaders.add(leader['guid'])
            print(f'create {name} ({fac} {kind}) leader {leader["name"]}')
            if ra:
                print('  ', ra.cmd(f'.guild create {leader["name"]} "{name}"')[:120])
                gid = db(f"SELECT guildid FROM guild WHERE name='{name}'")
                if not gid:
                    print('  create failed'); continue
                guilds[name] = int(gid[0][0]); leader['guild'] = guilds[name]
        if name in guilds and not a.dry_run:
            db(f"INSERT IGNORE INTO wov_guild_type VALUES ({guilds[name]}, '{kind}')")
    kinds = {int(g): k for g, k in db('SELECT guildid, kind FROM wov_guild_type')} if not a.dry_run else {guilds.get(n, -i): k for i, (f, k, n) in enumerate(PLAN)}
    fac_of = {}
    for f, k, n in PLAN:
        if n in guilds:
            fac_of[guilds[n]] = f
    size = {g: 0 for g in kinds}
    for c in chars:
        if c['guild'] in size:
            size[c['guild']] += 1
    pool = {g for g in kinds if g not in real and g in fac_of}
    # 2. choose who joins
    want = [c for c in chars if not c['guild'] and c['level'] >= 10 and stable(c['guid']) < target_pct(c['level'])]
    want.sort(key=lambda c: (-c['level'], stable(c['guid'] * 3)))
    invited, plan_counts = 0, {}
    for c in want:
        if invited >= a.max:
            break
        k = kind_for(c['level'], c['drive'], c['guid'])
        options = [g for g in pool if fac_of[g] == c['faction'] and kinds[g] == k] or [g for g in pool if fac_of[g] == c['faction'] and kinds[g] == 'mixed']
        if not options:
            continue
        g = min(options, key=lambda x: size[x])
        gname = next(n for n, i in guilds.items() if i == g)
        plan_counts[gname] = plan_counts.get(gname, 0) + 1
        if ra:
            out = ra.cmd(f'.guild invite {c["name"]} "{gname}"')
            if 'not found' in out.lower() or 'error' in out.lower():
                print('  invite failed', c['name'], out[:80]); continue
        size[g] += 1; invited += 1
        # a couple of officers per new guild: the first two level 40+ recruits
        if ra and size[g] <= 3 and c['level'] >= 40:
            ra.cmd(f'.guild rank {c["name"]} 1')
    if ra:
        ra.close()
    # 3. report coverage
    print('invited', invited, 'of', len(want), 'eligible;', plan_counts)
    for lo, hi in [(10, 19), (20, 39), (40, 60)]:
        band = [c for c in chars if lo <= c['level'] <= hi]
        if band:
            have = sum(1 for c in band if c['guild']) + (0 if a.dry_run else 0)
            print(f'  {lo}-{hi}: {have}/{len(band)} in a guild before this run')

if __name__ == '__main__':
    main()
