#!/usr/bin/env python3
"""Way of Vanilla: what each bot's player wants to DO (drive), from its profile (lore_character.temperament)
and its motivation text. Stored in wov_player.drive; mod-playerbots reads it with the play schedules and
uses it to weight what the bot does (RPG statuses), how eager it is for world PvP, and who posts LFG/WTS.

  python3 wov/drives.py            classify all, print the distribution
"""
import os, re, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
def db(sql):
    r = subprocess.run(["bash", "-c", ". ops/env.sh && db acore_characters -N --batch -e \"$Q\""], cwd=REPO,
                       env=dict(os.environ, Q=sql), capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr)
    return [l.split("\t") for l in r.stdout.splitlines()]

BY_PROFILE = {
    "pvp": {"PVP_HARDCORE", "PVP_TRASHTALKER", "DUELIST"},
    "dungeon": {"LFG_SPAMMER", "RAIDER", "HARDCORE_RAIDLEAD", "HEALER_MAIN", "MIN_MAXER", "BACKSEAT_TANK", "THEORYCRAFTER"},
    "gold": {"GOLD_FARMER", "LOOTGOBLIN", "TRADER", "HUMBLE_FARMER", "GATHERER", "FISHERMAN"},
    "level": {"SPEEDRUNNER", "QUEST_WHINER", "CASUAL", "SCARED_NEWBIE", "ALTOHOLIC", "KEYBOARD_TURNER"},
    "social": {"ROLEPLAYER", "WANDERING_RP", "EMOTE_SPAMMER", "TRADE_COMEDIAN", "GUILD_RECRUITER", "HYPE_MAN", "WOW_MOM",
               "CHILL_DAD", "DRAMA_QUEEN", "FOOL", "TWELVE_YEAR_OLD", "MENTOR"},
    "explore": {"EXPLORER", "LORE_NERD", "SUPERSTITIOUS", "CONSPIRACY_THEORIST"},
}
BY_TEXT = [("pvp", r"pvp|honou?r|battleground|warsong|arathi|alterac|gank|duel"),
           ("dungeon", r"dungeon|instance|raid|molten|attun|blackrock|stratholme|scholo|zul'?farrak|maraudon|scarlet|gear"),
           ("gold", r"gold|farm|profession|sell|auction|craft|herb|mining|skinning|fish"),
           ("level", r"level|reach|ding|quest"),
           ("social", r"guild|friend|people|social|chat"),
           ("explore", r"explore|lore|see the world|every zone")]

def main():
    db("ALTER TABLE wov_player ADD COLUMN drive VARCHAR(12) NOT NULL DEFAULT ''") if not db(
        "SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='wov_player' AND column_name='drive'") else None
    rows = db("SELECT w.guid, IFNULL(l.temperament,''), IFNULL(l.motivation_short,''), IFNULL(l.motivation,'') "
              "FROM wov_player w LEFT JOIN lore_character l ON l.guid=w.guid")
    counts = {}
    upd = {}
    for guid, temp, ms, mot in rows:
        text = (ms + " " + mot).lower()
        drive = ""
        for k, pat in BY_TEXT:          # what they want right now beats the general profile
            if re.search(pat, ms.lower()):
                drive = k
                break
        if not drive:
            drive = next((k for k, s in BY_PROFILE.items() if temp in s), "")
        if not drive:
            drive = next((k for k, pat in BY_TEXT if re.search(pat, text)), "")
        upd.setdefault(drive, []).append(guid)
        counts[drive] = counts.get(drive, 0) + 1
    for drive, guids in upd.items():
        for i in range(0, len(guids), 500):
            db(f"UPDATE wov_player SET drive='{drive}' WHERE guid IN ({','.join(guids[i:i+500])})")
    print({k or "-": v for k, v in sorted(counts.items(), key=lambda x: -x[1])})

if __name__ == "__main__":
    main()
