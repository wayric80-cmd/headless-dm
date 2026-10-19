#!/usr/bin/env python3
"""Way of Vanilla, part 2: a player behind every bot.

For each random bot, draws a player profile (the 53 templates) and has the model write who the
PERSON playing that character is: everyday life kept light, WoW history, how they come across, what
they want from the game now, and when/how long they play. Stored in HeadlessDM's lore_character
(so regard and the BIO_/BIOX_ projection work unchanged) plus wov_player for play schedules.

  python3 wov/gen_players.py sample [--n 3]      print, store nothing
  python3 wov/gen_players.py generate [--redo]   every bot without a player (or all with --redo)
  python3 wov/gen_players.py project             write BIO_/BIOX_ templates and assignments
Then: ra "ollama reload".
"""
import argparse, json, os, random, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "services", "lore"))
import gen_backstories as gb  # noqa: E402  (sql, q, ensure_schema, project)

ROUTER = "http://127.0.0.1:11434/api/generate"
MODEL_TAG = "qwen3-8b/wov-player-v1"
WEIGHTS = json.load(open(os.path.join(HERE, "sql", "player-weights.json")))
RACE = {1: "Human", 2: "Orc", 3: "Dwarf", 4: "Night Elf", 5: "Undead", 6: "Tauren", 7: "Gnome", 8: "Troll"}
CLASS = {1: "Warrior", 2: "Paladin", 3: "Hunter", 4: "Rogue", 5: "Priest", 7: "Shaman", 8: "Mage", 9: "Warlock", 11: "Druid"}
BANNED = re.compile(r"\b(outland|northrend|death knight|blood elf|draenei|arena|achievement|flying mount|"
                    r"dungeon finder|lich king|burning crusade|wrath|cataclysm|level (?:6[1-9]|7\d|80)|"
                    r"as an ai|language model|i am a bot|azeroth is real|vanilla|classic wow|halls of|heroic|titan|20(?:0[0-9]|1[0-9]))\b", re.I)


LIVES = ["a teenager in high school", "a university student", "a nurse working rotating shifts", "an office worker",
         "a stay-at-home parent of two", "a truck driver home on weekends", "a retired teacher", "a cook in a restaurant",
         "an IT support worker", "between jobs and playing a lot", "a factory worker on night shifts", "a soldier on leave",
         "a dad with a newborn", "a couple who play together", "a shop clerk", "a programmer", "an electrician",
         "a college dropout living with roommates", "a mother whose kids got her into the game", "a student on summer break"]
EXPS = ["WoW is their first online game", "played EverQuest for years before", "came from Ultima Online",
        "played Warcraft III and loves the lore", "a friend talked them into it a few weeks ago",
        "has played since launch and has alts", "returned after a break", "plays mostly with real-life friends",
        "used to raid hard in another game", "new to MMOs but plays a lot of console games"]
SCHED = [("most evenings", (18, 21), (60, 180)), ("weekends", (10, 20), (120, 300)), ("almost every day", (16, 22), (90, 240)),
         ("irregularly", (8, 23), (20, 120)), ("late at night", (22, 23), (60, 180)), ("in short sessions after work", (17, 20), (20, 60)),
         ("on weekday mornings", (7, 11), (45, 120))]

GOALS = [(9, ["learn the class and reach level 10 for talents", "find people to quest with", "figure out the game and not die so much", "pick professions and start gathering"]),
         (19, ["run the first dungeons for blue gear", "save gold for riding at 20", "level a gathering profession", "join a friendly guild"]),
         (29, ["get the first mount and some dungeon gear", "try battlegrounds now that they are open", "level professions to make money", "keep up with guild friends"]),
         (39, ["run Scarlet Monastery for gear", "save up for faster riding at 40", "get the profession to artisan levels", "world PvP in Stranglethorn Vale"]),
         (49, ["get through the 40s quickly", "farm gold for the next mount and gear", "run Zul'Farrak and Maraudon", "climb the honor ranks"]),
         (60, ["reach 60", "collect pre-raid gear from Blackrock Depths and Stratholme", "get attuned and into Molten Core", "farm gold and consumables for raids"])]
def goal_for(level, rng):
    for top, opts in GOALS:
        if level <= top:
            return rng.choice(opts)
    return rng.choice(GOALS[-1][1])

PROMPT = """Invent the real person who plays a World of Warcraft character on a Vanilla server (original game, level cap 60, around 2005). The character: {name}, a level {level} {race} {cls}, {faction}{guild}. The player's style: {profile}

Write about the PERSON at the keyboard, not the character's in-game story. Keep everyday life light and generic (student, works shifts, parent, retired, between jobs...), no real names, no real cities, nothing sensitive. Their goals must fit level {level} and the original game only. Who they are: {life}. Their WoW experience: {exp}. They play {days}, usually logging on around {hour}:00 for about {mins} minutes. A goal that fits where they are now: {goal}. Gold and loot exist only inside the game. Never call the game Vanilla or Classic and never mention years: to them this is simply WoW, the current game.

Reply with ONLY a JSON object with these keys:
"player": 1-2 sentences, second person ("You are..."), who you are away from the game.
"personality": second person, 2-3 traits, how you come across in chat and in groups, at most 35 words.
"gist": second person, your WoW history and situation (how long you have played, alts, friends, guild feelings), at most 45 words.
"motivation": second person, what you want from the game right now and why, 35-60 words.
"motivation_short": the motivation in one short line."""

def bots():
    rows = gb.sql("SELECT c.guid, c.name, c.level, c.race, c.class, IFNULL(gm.guildid,0), IFNULL(g.name,'') "
                  "FROM characters c JOIN acore_auth.account a ON a.id = c.account "
                  "LEFT JOIN guild_member gm ON gm.guid = c.guid LEFT JOIN guild g ON g.guildid = gm.guildid "
                  "WHERE a.username LIKE 'RNDBOT%' ORDER BY c.online DESC, c.guid")
    return [dict(guid=int(r[0]), name=r[1], level=int(r[2]), race=int(r[3]), cls=int(r[4]),
                 guildid=int(r[5]), guild=r[6]) for r in rows]

def templates():
    return {r[0]: r[1] for r in gb.sql("SELECT `key`, prompt FROM mod_ollama_chat_personality_templates "
                                       "WHERE `key` NOT LIKE 'BIO%'")}

def current(guid):
    r = gb.sql(f"SELECT personality FROM mod_ollama_chat_personality WHERE guid = {guid}")
    return r[0][0] if r and not r[0][0].startswith("BIO") else None

def ask(prompt):
    body = {"model": "prose", "prompt": prompt, "stream": False, "format": "json",
            "options": {"temperature": 0.95, "num_predict": 450}}
    req = urllib.request.Request(ROUTER, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["response"]

KEYS = ("player", "personality", "gist", "motivation", "motivation_short")
def write_one(b, tmpl, rng):
    days, hr, mn = rng.choice(SCHED)
    b = dict(b, life=rng.choice(LIVES), exp=rng.choice(EXPS), days=days, hour=rng.randint(*hr), mins=rng.randrange(mn[0], mn[1] + 1, 10), goal=goal_for(b["level"], rng))
    faction = "Horde" if b["race"] in (2, 5, 6, 8) else "Alliance"
    key = current(b["guid"])
    if key not in tmpl:
        keys = [k for k in tmpl]; key = rng.choices(keys, [WEIGHTS.get(k, 100) for k in keys])[0]
    p = PROMPT.format(name=b["name"], level=b["level"], race=RACE.get(b["race"], "?"),
                      cls=CLASS.get(b["cls"], "?"), faction=faction,
                      guild=f", member of the guild {b['guild']}" if b["guild"] else ", not in a guild",
                      profile=tmpl[key], life=b["life"], exp=b["exp"], days=b["days"], hour=b["hour"], mins=b["mins"], goal=b["goal"])
    for attempt in range(3):
        try:
            d = json.loads(ask(p).split("</think>")[-1])
            if all(isinstance(d.get(k), str) and d[k].strip() for k in KEYS):
                text = " ".join(d[k] for k in KEYS)
                if BANNED.search(text):
                    continue
                d["temperament"] = key
                d.update(play_days=b["days"], play_start_hour=b["hour"], session_minutes=b["mins"])
                return d
        except Exception as e:  # noqa: BLE001
            gb.log(f"{b['name']}: attempt {attempt+1} failed: {e}")
    return None

def store(b, d):
    hour = int(d["play_start_hour"]) % 24
    mins = int(d["session_minutes"])
    gb.sql("REPLACE INTO lore_character (guid, guildid, temperament, backstory, personality, gist, motivation, "
           "motivation_short, model, era) VALUES "
           f"({b['guid']}, {b['guildid'] or 'NULL'}, {gb.q(d['temperament'])}, {gb.q(d['player'] + ' ' + d['gist'])}, "
           f"{gb.q(d['personality'][:400])}, {gb.q(d['gist'][:600])}, {gb.q(d['motivation'])}, "
           f"{gb.q(d['motivation_short'][:255])}, {gb.q(MODEL_TAG)}, 'classic');"
           "CREATE TABLE IF NOT EXISTS wov_player (guid INT UNSIGNED NOT NULL PRIMARY KEY, play_days VARCHAR(32) NOT NULL, "
           "play_start_hour TINYINT UNSIGNED NOT NULL, session_minutes SMALLINT UNSIGNED NOT NULL, "
           "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP) "
           "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
           f"REPLACE INTO wov_player (guid, play_days, play_start_hour, session_minutes) VALUES "
           f"({b['guid']}, {gb.q(str(d.get('play_days', 'irregular'))[:32])}, {hour}, {mins});", fetch=False)

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--n", type=int, default=3)
    g = sub.add_parser("generate"); g.add_argument("--redo", action="store_true")
    sub.add_parser("project")
    a = ap.parse_args()
    if a.cmd == "project":
        return gb.project(None)
    gb.ensure_schema()
    tmpl, rng, all_bots = templates(), random.Random(), bots()
    if a.cmd == "sample":
        for b in rng.sample(all_bots, min(a.n, len(all_bots))):
            d = write_one(b, tmpl, rng)
            print(f"\n== {b['name']} (lvl {b['level']} {RACE.get(b['race'])} {CLASS.get(b['cls'])}) ==")
            print(json.dumps(d, indent=2, ensure_ascii=False))
        return 0
    have = set() if a.redo else {int(r[0]) for r in gb.sql("SELECT guid FROM lore_character")}
    todo = [b for b in all_bots if b["guid"] not in have]
    gb.log(f"{len(todo)} bots to write"); t0 = time.time(); ok = 0
    for i, b in enumerate(todo, 1):
        d = write_one(b, tmpl, rng)
        if d:
            store(b, d); ok += 1
        gb.log(f"[{i}/{len(todo)}] {b['name']}: {'ok' if d else 'FAILED'}")
    gb.log(f"done: {ok}/{len(todo)} in {time.time()-t0:.0f}s")
    return 0

if __name__ == "__main__":
    sys.exit(main())
