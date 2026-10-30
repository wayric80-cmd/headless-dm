#!/usr/bin/env python3
"""Way of Vanilla: content phases on a fixed schedule (wov/conf/phases.json).

    python3 wov/phases.py status            phases, dates, what is live, what is locked
    python3 wov/phases.py move N YYYY-MM-DD  move phase N earlier or later (clear: move N week)
    python3 wov/phases.py sync              (re)write the quest/map locks for phases not yet live, reload disables
    python3 wov/phases.py tick [--dry-run]  hourly (wov-phases.timer): sync, announce 7/1 days ahead, and on the day at
                                            restart_hour switch the phase's brackets on and restart wow-world gracefully
    python3 wov/phases.py apply N           switch phase N on now (restart with countdown)
    python3 wov/phases.py open-gates        Ahn'Qiraj: the war effort is done, open AQ20/AQ40 (restart with countdown)
Before the launch (no logs/fresh-start-at) only phase 1 is live and nothing is scheduled.
Locks: acore_world.disables rows with comment 'wov-phase ...' (quests sourceType 1, maps sourceType 2). The progression
module's own SQL may delete rows for the same entries when a bracket is switched on: sync puts them back.
"""
import datetime as dt, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.realpath(__file__)); REPO = os.path.dirname(HERE)
CONF = os.path.join(HERE, 'conf', 'phases.json'); STATE = os.path.join(REPO, 'logs', 'phases-state.json')
OVR = os.path.join(HERE, 'conf', 'progression_system.wov.overrides')
DRY = '--dry-run' in sys.argv

def sh(cmd):
    return subprocess.run(['bash', '-c', f'cd {REPO} && . ops/env.sh && {cmd}'], capture_output=True, text=True)
def sql(q, db='acore_world'):
    r = subprocess.run(['bash', '-c', f'cd {REPO} && . ops/env.sh && db {db} -N -B'], input=q, capture_output=True, text=True)
    if r.returncode: sys.exit(f'sql failed: {r.stderr.strip()}')
    return [l.split('\t') for l in r.stdout.splitlines() if l]
def ra(cmd):
    if DRY: print(f'[dry] ra {cmd}'); return ''
    return sh(f'ra {json.dumps(cmd)}').stdout
def load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except FileNotFoundError: return d
def save(p, o):
    if DRY: return
    tmp = p + '.tmp'; json.dump(o, open(tmp, 'w', encoding='utf-8'), indent=2, ensure_ascii=False); os.replace(tmp, p)

C = load(CONF, None); S = load(STATE, {'live': [1], 'announced': {}, 'aq_gates_open': False})

def launch():
    try: return dt.datetime.fromtimestamp(float(open(os.path.join(REPO, 'logs', 'fresh-start-at')).read().split()[0]))
    except (FileNotFoundError, ValueError, IndexError): return None
def due(p):
    if p.get('date'): return dt.datetime.strptime(p['date'], '%Y-%m-%d').replace(hour=C['restart_hour'])
    L = launch()
    if not L: return None
    d = (L + dt.timedelta(weeks=p['week'])).replace(hour=C['restart_hour'], minute=0, second=0, microsecond=0)
    return d if p['week'] else L
def phase(n): return next(p for p in C['phases'] if p['n'] == n)

def wanted_locks():
    """(sourceType, entry, why) for everything not live yet"""
    out = []
    for p in C['phases']:
        if p['n'] in S['live']: continue
        out += [(1, q, f"wov-phase {p['n']}") for q in quest_ids(p)]
    g = C['aq_gates']
    if not S['aq_gates_open']:
        out += [(1, q, 'wov-phase aq-gates') for q in quest_ids(g)]
        out += [(2, m, 'wov-phase aq-gates') for m in g['lock_maps']]
    if 5 not in S['live']: out.append((2, 533, 'wov-phase 5'))
    seen, res = set(), []
    for t, e, w in out:
        if (t, e) not in seen: seen.add((t, e)); res.append((t, e, w))
    return res
def quest_ids(p):
    conds = []
    if p.get('lock_quest_sort'): conds.append(f"QuestSortID IN ({','.join(map(str, p['lock_quest_sort']))})")
    if p.get('lock_quest_ids'): conds.append(f"ID IN ({','.join(map(str, p['lock_quest_ids']))})")
    for f in p.get('lock_quest_faction', []):
        conds.append(f"{f} IN (RewardFactionID1,RewardFactionID2,RewardFactionID3,RewardFactionID4,RewardFactionID5)")
    if not conds: return []
    return [int(r[0]) for r in sql(f"SELECT ID FROM quest_template WHERE {' OR '.join(conds)};")]

def sync(verbose=True):
    want = wanted_locks()
    have = {(int(t), int(e)): c for t, e, c in sql("SELECT sourceType, entry, comment FROM disables WHERE sourceType IN (1,2);")}
    add = [(t, e, w) for t, e, w in want if (t, e) not in have]
    ours = {k for k, c in have.items() if c.startswith('wov-phase')}
    drop = sorted(ours - {(t, e) for t, e, _ in want})
    if verbose or add or drop:
        print(f"locks: {len(want)} wanted, {len(add)} to add, {len(drop)} to remove")
    if DRY or not (add or drop): return bool(add or drop)
    q = ''.join(f"INSERT IGNORE INTO disables (sourceType, entry, flags, params_0, params_1, comment) VALUES ({t}, {e}, {15 if t == 2 else 0}, '', '', '{w}');\n" for t, e, w in add)
    q += ''.join(f"DELETE FROM disables WHERE sourceType={t} AND entry={e} AND comment LIKE 'wov-phase%';\n" for t, e in drop)
    sql(q); ra('reload disables')
    return True

def set_brackets(brs):
    lines = open(OVR, encoding='utf-8').read().rstrip('\n').split('\n')
    for b in brs:
        key = f'ProgressionSystem.Bracket_{b}'
        if any(re.match(rf'^{re.escape(key)}\s*=', l) for l in lines):
            lines = [f'{key} = 1' if re.match(rf'^{re.escape(key)}\s*=', l) else l for l in lines]
        else: lines.append(f'{key} = 1')
    if DRY: print('[dry] overrides:', brs); return
    open(OVR, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    r = subprocess.run(['python3', os.path.join(HERE, 'apply-overlay.py')], capture_output=True, text=True); print(r.stdout.strip())
    # our Bracket_Custom files run again after the new bracket's SQL at the next start
    sql("DELETE FROM updates WHERE name LIKE 'progression_custom_wov%';")

def restart(why):
    sec = C['restart_countdown_sec']
    ra(f'announce {why} Server restart in {sec // 60} minutes.')
    print(ra(f'server restart {sec}').strip() or f'restart in {sec}s requested')

def mail(subject, text):
    try:
        sys.path.insert(0, HERE); import watch; watch.mail(subject, text)
    except Exception as e: print('mail failed:', e)

def go_live(n):
    p = phase(n)
    if p.get('requires') and not S.get(p['requires']):
        msg = f"Phase {n} ({p['name']}) is due but needs {p['requires']}: not switched on."
        print(msg)
        if not S['announced'].get(f'{n}:blocked'): mail(f'WoV: phase {n} blocked', msg); S['announced'][f'{n}:blocked'] = 1; save(STATE, S)
        return False
    set_brackets(p.get('brackets', []))
    S['live'] = sorted(set(S['live']) | {n}); save(STATE, S)
    sync()
    restart(f"Patch day: {p['name']} is open!")
    mail(f"WoV: phase {n} live – {p['name']}", f"Phase {n} ({p['name']}) switched on {dt.datetime.now():%Y-%m-%d %H:%M}, brackets {p.get('brackets')}. wow-world restarts in {C['restart_countdown_sec']//60} min.")
    return True

def status():
    L = launch(); print(f"launch: {L:%Y-%m-%d %H:%M}" if L else "launch: not yet (fresh start not run) – only phase 1, nothing scheduled")
    for p in C['phases']:
        d = due(p); live = p['n'] in S['live']
        print(f"  {p['n']}. {p['name']:<28} {'LIVE' if live else (f'{d:%Y-%m-%d %H:%M}' if d else 'after launch +'+str(p['week'])+'w')}"
              f"{'  (moved)' if p.get('date') else ''}{'  needs '+p['requires'] if p.get('requires') and not S.get(p['requires']) else ''}")
    print(f"  AQ gates: {'open' if S['aq_gates_open'] else 'shut'}")
    rows = sql("SELECT comment, sourceType, COUNT(*) FROM disables WHERE comment LIKE 'wov-phase%' GROUP BY comment, sourceType ORDER BY comment;")
    for c, t, n in rows: print(f"  lock {c}: {n} {'quests' if t == '1' else 'maps'}")

cmd = (sys.argv[1:] or ['status'])[0]
if cmd == 'status': status()
elif cmd == 'sync': sync()
elif cmd == 'move':
    n, d = int(sys.argv[2]), sys.argv[3]
    p = phase(n)
    if d == 'week': p.pop('date', None)
    else: dt.datetime.strptime(d, '%Y-%m-%d'); p['date'] = d
    for k in [k for k in S['announced'] if k.startswith(f'{n}:')]: del S['announced'][k]
    save(CONF, C); save(STATE, S); status()
elif cmd == 'apply': go_live(int(sys.argv[2]))
elif cmd == 'open-gates':
    S['aq_gates_open'] = True; save(STATE, S); set_brackets(C['aq_gates']['brackets']); sync()
    restart("The Scarab Gong has been rung: the gates of Ahn'Qiraj are open!")
elif cmd == 'tick':
    sync(verbose=False)
    now = dt.datetime.now()
    for p in C['phases']:
        n, d = p['n'], due(p)
        if n in S['live'] or not d: continue
        if now >= d: go_live(n); break  # one phase per restart
        for days in C['announce_days']:
            key = f'{n}:{days}'
            if now >= d - dt.timedelta(days=days) and not S['announced'].get(key):
                when = 'tomorrow' if days == 1 else f'in {days} days'
                ra(f"announce {p['name']} opens {when} ({d:%A %d %B}).")
                mail(f"WoV: phase {n} {when}", f"{p['name']} goes live {d:%Y-%m-%d %H:%M} (automatic restart with {C['restart_countdown_sec']//60} min countdown). Move it: python3 wov/phases.py move {n} YYYY-MM-DD")
                S['announced'][key] = 1; save(STATE, S)
else: sys.exit(__doc__)
