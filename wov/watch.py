#!/usr/bin/env python3
"""wov: watch the realm and mail the operator.

  watch.py check   every 10 min: mail at once if wow-world crashed/restarted on its own, or a service is down
  watch.py daily   once a day: a short status mail (uptime, crashes, online, Haiku use, realm news)
  watch.py daily --dry-run   print instead of mailing

Mail goes through Resend with the portal's key (/opt/wow/portal/portal.env), to WOV_WATCH_TO.
No secrets are printed or mailed. Read-only apart from its own state file.
"""
import json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE = os.path.join(REPO, 'logs', 'watch-state.json')
TO = os.environ.get('WOV_WATCH_TO', 'way.ric80@gmail.com')
SYSTEM = ['wow-world', 'wow-auth', 'wow-router']
USER = ['wov-portal', 'wov-tunnel', 'wov-guild-fill.timer']

def sh(cmd, env=None):
    r = subprocess.run(['bash', '-c', cmd], cwd=REPO, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    return r.stdout.strip()

def db(sql, dbname='acore_characters'):
    out = sh(f'. ops/env.sh >/dev/null 2>&1 && db {dbname} -N --batch -e "$Q"', {'Q': sql})
    return [l.split('\t') for l in out.splitlines() if l]

def portal_env():
    env = {}
    try:
        for line in open('/opt/wow/portal/portal.env'):
            m = re.match(r'^([A-Z_]+)=(.*)$', line.strip())
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"')
    except OSError:
        pass
    return env

def mail(subject, text):
    env = portal_env()
    key, sender = env.get('RESEND_API_KEY'), env.get('PORTAL_MAIL_FROM')
    if not key or not sender:
        print('no mail settings; would send:', subject); print(text); return False
    body = json.dumps({'from': sender, 'to': [TO], 'subject': subject, 'text': text}).encode()
    req = urllib.request.Request('https://api.resend.com/emails', data=body, method='POST',
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
                                          'User-Agent': 'wov-watch/1'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except Exception as e:  # noqa: BLE001
        print('mail failed:', type(e).__name__, getattr(e, 'code', ''))
        return False

def unit(name, user=False):
    pre = 'XDG_RUNTIME_DIR=/run/user/1000 systemctl --user' if user else 'systemctl'
    out = sh(f'{pre} show {name} -p ActiveState -p NRestarts -p ActiveEnterTimestamp -p MainPID')
    return dict(l.split('=', 1) for l in out.splitlines() if '=' in l)

def journal(unit_name, since):
    return sh(f'journalctl -u {unit_name} --since "{since}" --no-pager -o short-iso 2>/dev/null')

def load():
    try:
        return json.load(open(STATE))
    except Exception:  # noqa: BLE001
        return {}

def save(s):
    json.dump(s, open(STATE + '.tmp', 'w')); os.replace(STATE + '.tmp', STATE)

def crashes(since):
    return [l for l in journal('wow-world', since).splitlines() if re.search(r'code=(dumped|killed)|status=(11|6|9)/', l)]

def online():
    r = db("SELECT COUNT(*), SUM(a.username NOT LIKE 'RNDBOT%') FROM characters c JOIN acore_auth.account a ON a.id=c.account WHERE c.online=1")
    return (int(r[0][0] or 0), int(r[0][1] or 0)) if r else (0, 0)

def check():
    s = load(); now = time.time(); problems = []
    since = datetime.fromtimestamp(s.get('last_check', now - 900)).strftime('%Y-%m-%d %H:%M:%S')
    for c in crashes(since):
        problems.append('wow-world: ' + c.split(' ', 1)[-1])
    for name in SYSTEM:
        if unit(name).get('ActiveState') != 'active':
            problems.append(f'{name} is {unit(name).get("ActiveState")}')
    for name in USER:
        st = unit(name, True).get('ActiveState')
        if st != 'active':
            problems.append(f'{name} (user) is {st}')
    w = unit('wow-world')
    if s.get('world_start') and w.get('ActiveEnterTimestamp') != s['world_start'] and not crashes(since):
        problems.append(f'wow-world restarted at {w.get("ActiveEnterTimestamp")} (no crash in the journal: planned restart?)')
    s['world_start'] = w.get('ActiveEnterTimestamp'); s['last_check'] = now
    if problems and now >= s.get('alert_quiet_until', 0):
        total, real = online()
        text = 'Way of Vanilla watch found:\n\n- ' + '\n- '.join(problems) + \
               f'\n\nNow: wow-world {w.get("ActiveState")} since {w.get("ActiveEnterTimestamp")}, {total} online ({real} real players).\n' \
               '\nThe service restarts itself (Restart=always). Nothing was changed by this check.'
        if mail('[Way of Vanilla] ' + problems[0][:70], text):
            s['alert_quiet_until'] = now + 3600
    save(s)
    print('ok' if not problems else 'problems: ' + '; '.join(problems))

def haiku(since):
    lines = [l for l in journal('wow-router', since).splitlines() if 'backend=haiku ok' in l]
    tin = tout = 0; cost = 0.0; priced = 0
    for l in lines:
        m = re.search(r'(\d+)\+(\d+)tok', l)
        if m:
            tin += int(m.group(1)); tout += int(m.group(2))
        c = re.search(r'\$(\d+\.\d+)', l)
        if c:
            cost += float(c.group(1)); priced += 1
    fails = len([l for l in journal('wow-router', since).splitlines() if 'FAIL' in l])
    return len(lines), tin, tout, (cost if priced else None), fails

def daily(dry):
    since = datetime.fromtimestamp(time.time() - 86400).strftime('%Y-%m-%d %H:%M:%S')
    w = unit('wow-world'); total, real = online()
    cr = crashes(since)
    calls, tin, tout, cost, fails = haiku(since)
    est = cost if cost is not None else calls * 0.0003
    def one(sql, dbn='acore_characters'):
        r = db(sql, dbn); return r[0][0] if r and r[0] and r[0][0] not in (None, 'NULL') else '0'
    quests = one("SELECT COUNT(*) FROM ledger_event WHERE event_type='quest_complete' AND ts >= NOW() - INTERVAL 1 DAY")
    dings = one("SELECT COUNT(*) FROM ledger_event WHERE event_type='level_up' AND ts >= NOW() - INTERVAL 1 DAY AND JSON_VALID(detail) AND JSON_EXTRACT(detail,'$.new')=JSON_EXTRACT(detail,'$.old')+1")
    kills = one("SELECT COUNT(*) FROM ledger_event WHERE event_type='pvp_kill' AND ts >= NOW() - INTERVAL 1 DAY")
    battles = one("SELECT COUNT(*) FROM wov_battle WHERE ended >= NOW() - INTERVAL 1 DAY")
    accounts = one("SELECT COUNT(*) FROM account WHERE joindate >= NOW() - INTERVAL 1 DAY AND username NOT LIKE 'RNDBOT%'", 'acore_auth')
    logins = one("SELECT COUNT(*) FROM account WHERE last_login >= NOW() - INTERVAL 1 DAY AND username NOT LIKE 'RNDBOT%'", 'acore_auth')
    anchors = one("SELECT COUNT(*) FROM playerbots_bot_anchor", 'acore_playerbots')
    disk = sh("df -h /opt/wow | awk 'NR==2{print $4\" free of \"$2}'")
    mem = sh("free -m | awk '/Mem:/{print $7\" MiB available of \"$2}'")
    units = ', '.join(f'{n} {unit(n).get("ActiveState")}' for n in SYSTEM) + ', ' + \
            ', '.join(f'{n} {unit(n, True).get("ActiveState")}' for n in USER)
    text = f"""Way of Vanilla – daily status {datetime.now():%Y-%m-%d %H:%M}

Server
- wow-world running since {w.get('ActiveEnterTimestamp')}
- Crashes last 24 h: {len(cr)}{''.join(chr(10) + '    ' + c for c in cr[:5])}
- Services: {units}
- Online now: {total} ({real} real players)
- Disk: {disk}. Memory: {mem}

AI
- Haiku replies last 24 h: {calls} ({tin}+{tout} tokens), {'cost' if cost is not None else 'estimated'} ${est:.2f}
- Failed model calls last 24 h: {fails} (the local Qwen server is off during the trip, so these are expected)

Realm last 24 h
- {quests} quests, {dings} levels gained, {kills} PvP kills, {battles} Call to Arms battles
- New game accounts: {accounts}. Real accounts that logged in: {logins}
- Bots whose progression is kept: {anchors}

War room: https://wayofvanilla.se/#dashboard
"""
    if dry:
        print(text); return
    print('sent' if mail(f'[Way of Vanilla] Daily status: {len(cr)} crash(es), {total} online', text) else 'not sent')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if mode == 'daily':
        daily('--dry-run' in sys.argv)
    else:
        check()
