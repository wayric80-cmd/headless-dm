#!/usr/bin/env python3
"""Way of Vanilla: when is the player behind each bot online? Reference implementation of the C++ logic in
mod-playerbots (RandomPlayerbotMgr.cpp, Wov* helpers). Keep both in sync.

  python3 wov/wov_schedule.py sim            simulated online count per hour for the coming week
  python3 wov/wov_schedule.py now            how many scheduled players are online right now
"""
import sys, time, subprocess, os
M = (1 << 64) - 1
PCT = int(os.environ.get("WOV_SESSION_PCT", "200"))   # AiPlayerbot.WoV.Schedule.SessionPercent

def h(a, b):
    x = (a * 0x9E3779B97F4A7C15 + b * 0xBF58476D1CE4E5B9 + 0x94D049BB133111EB) & M
    x ^= x >> 31; x = (x * 0xBF58476D1CE4E5B9) & M; x ^= x >> 29
    return x

def tz_offset_hours(guid):            # where the player lives, relative to the server (Sweden)
    b = h(guid, 7) % 100
    if b < 45: return 0                # Scandinavia / central Europe
    if b < 60: return -1               # UK / Ireland / Portugal
    if b < 82: return -6               # US east
    if b < 94: return -9               # US west
    return 8                           # Australia

def play_prob(days, weekday):         # weekday: 0=Sun .. 6=Sat
    we = weekday in (0, 6)
    return {"almost every day": 90, "most evenings": 70, "late at night": 60, "irregularly": 40,
            "weekends": 90 if we else (30 if weekday == 5 else 10),
            "on weekday mornings": 20 if we else 80,
            "in short sessions after work": 30 if we else 80}.get(days, 50)

def online(guid, days, start_hour, mins, now, server_gmtoff):
    sec = now + server_gmtoff + tz_offset_hours(guid) * 3600
    day, minute = sec // 86400, (sec % 86400) // 60
    for dd in (day, day - 1):
        wd = (dd + 4) % 7
        if h(guid, dd * 8 + 1) % 100 >= play_prob(days, wd):
            continue
        st = start_hour * 60 + int(h(guid, dd * 8 + 2) % 81) - 40
        ln = mins * (70 + int(h(guid, dd * 8 + 3) % 71)) // 100
        ln = ln * PCT // 100
        m = minute + (day - dd) * 1440
        if st <= m < st + ln:
            return True
    return False

def rows():
    out = subprocess.run(["bash", "-c", ". ops/env.sh && db acore_characters -N -e "
                          "'SELECT guid, play_days, play_start_hour, session_minutes FROM wov_player'"],
                         capture_output=True, text=True, cwd=os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")).stdout
    return [(int(g), d, int(s), int(m)) for g, d, s, m in (l.split("\t") for l in out.strip().splitlines())]

if __name__ == "__main__":
    R = rows(); off = time.localtime().tm_gmtoff; t0 = int(time.time()) // 3600 * 3600
    if sys.argv[1] == "now":
        print(sum(online(*r, int(time.time()), off) for r in R), "of", len(R))
    else:
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        for k in range(0, 168, step):
            t = t0 + k * 3600; n = sum(online(*r, t, off) for r in R)
            print(time.strftime("%a %H:00", time.localtime(t)), str(n).rjust(4), "#" * (n // 4))
