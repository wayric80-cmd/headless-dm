#!/usr/bin/env python3
"""Way of Vanilla: levelling tempo of the test batch of new bots (31/10, guid list in logs/newbots-20261031.txt).

    python3 wov/tempo.py snap      store level + played time of every bot in the batch (wov-tempo.timer, every 15 min)
    python3 wov/tempo.py report    played minutes per level 1->2 ... 9->10 (median, p25-p75, bots), from level 1 after
                                   the bot's fresh-start provisioning (AiPlayerbot.WoV.FreshStart = 10)

Played time is characters.totaltime (seconds). A bot counts from the first snapshot where it is level 1 AND marked
wov_fresh = 10, so the hour some of them spent at a random level before the provisioning does not count.
Test data only: drop table wov_tempo and the timer after the measurement.
"""
import os, statistics, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def db(q, d='acore_characters'):
    r = subprocess.run(['bash', '-c', f'. ops/env.sh >/dev/null 2>&1; db {d} -N -e "{q}"'], cwd=REPO,
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    return [l.split('\t') for l in r.stdout.splitlines() if l]


ids = open(os.path.join(REPO, 'logs', 'newbots-20261031.txt')).read().strip()
cmd = (sys.argv[1:] or ['report'])[0]
if cmd == 'snap':
    db('CREATE TABLE IF NOT EXISTS wov_tempo (guid INT UNSIGNED, ts DATETIME DEFAULT CURRENT_TIMESTAMP, level TINYINT '
       'UNSIGNED, totaltime INT UNSIGNED, fresh TINYINT, PRIMARY KEY (guid, ts))')
    fresh = {r[0] for r in db(f"SELECT bot FROM playerbots_random_bots WHERE event='wov_fresh' AND value=10 "
                              f"AND bot IN ({ids})", 'acore_playerbots')}
    rows = db(f'SELECT guid, level, totaltime FROM characters WHERE guid IN ({ids})')
    vals = ','.join(f"({g},{l},{t},{1 if g in fresh else 0})" for g, l, t in rows)
    db(f'INSERT IGNORE INTO wov_tempo (guid, level, totaltime, fresh) VALUES {vals}')
    print(f'{len(rows)} bots, {len(fresh)} provisioned at level 1')
elif cmd == 'report':
    snaps = {}
    for g, l, t, f in db('SELECT guid, level, totaltime, fresh FROM wov_tempo ORDER BY guid, ts'):
        snaps.setdefault(g, []).append((int(l), int(t), int(f)))
    per = {lv: [] for lv in range(1, 10)}
    started = 0
    for g, ss in snaps.items():
        i0 = next((i for i, (l, t, f) in enumerate(ss) if f and l == 1), None)
        if i0 is None:
            continue
        started += 1
        first = {}  # level -> played seconds when first seen at that level
        for l, t, f in ss[i0:]:
            first.setdefault(l, t)
        lv = sorted(first)
        for a, b in zip(lv, lv[1:]):
            if b == a + 1 and a < 10:
                per[a].append((first[b] - first[a]) / 60)
    print(f'bots from level 1: {started}')
    print('level   bots  median min  p25-p75')
    for lv in range(1, 10):
        v = sorted(per[lv])
        if not v:
            print(f'{lv:>2}->{lv+1:<3} {0:>4}')
            continue
        q = statistics.quantiles(v, n=4) if len(v) >= 4 else [v[0], 0, v[-1]]
        print(f'{lv:>2}->{lv+1:<3} {len(v):>4}  {statistics.median(v):>10.0f}  {q[0]:.0f}-{q[-1]:.0f}')
    lv = db(f'SELECT level, COUNT(*) FROM characters WHERE guid IN ({ids}) GROUP BY level ORDER BY level')
    print('now: ' + ', '.join(f'L{l}:{n}' for l, n in lv))
