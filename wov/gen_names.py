#!/usr/bin/env python3
"""Way of Vanilla: player-style character names ("Sirkillalot", "Mookin", "Jonbonejovi").

  python3 wov/gen_names.py generate --n 3000      ask the person route (Haiku) for names -> wov/names/player-names.txt
  python3 wov/gen_names.py check                  stats for the file
Names are filtered to what the WoW client/server accept: 3-12 letters, capital first, no 3 equal letters in a row.
"""
import argparse, json, os, random, re, sys, urllib.request
HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "names", "player-names.txt")
ROUTER = "http://127.0.0.1:11434/api/generate"
STYLES = [
    "puns on the class or on killing/healing (Sirkillalot, Healsonwheels, Stabbyou, Shamwow)",
    "mangled pop-culture, music, film and celebrity names (Jonbonejovi, Chucknourish, Legolaz, Gandalfx)",
    "food and silly words (Mookin, Porkchopz, Cheddarz, Bubblez)",
    "edgy teenage names with doubled or swapped letters (Shadoww, Deathbringr, Darkkness, Xarthas)",
    "short real first names or nicknames, often with a twist (Steve, Bobbo, Kev, Mikey, Jenni, Thommo)",
    "lazy or joke names (Afkbrb, Notahealer, Lootninja, Ganklord, Lolzor, Imnotabot excluded)",
    "names that sound like normal fantasy names but slightly off (Arthaas, Ilidan, Thrallz, Drizzit)",
    "words from other languages a European or American player might pick (Elmuerto, Sonnenschein, Kotik, Smaskens)",
]
PROMPT = ("Make up {n} World of Warcraft character names the way real players picked them on a busy server in 2005, "
          "in this style: {style}. Mix humour, laziness and attitude like real people. Each name is ONE word, letters "
          "A-Z only, 3 to 12 letters, no numbers, no spaces, no apostrophes. Do not use names of real living politicians, "
          "no slurs, nothing sexual, no hate. Do not use 'bot', 'ai' or 'npc' in a name. Reply with only a JSON list of strings.")
BAD = re.compile(r"(bot|npc|gm|admin|blizz|nigg|fag|rape|nazi|hitler|jew|cum|cock|dick|puss|anal|porn|sex|fuck|shit|cunt|whore|slut|retard|ai$)", re.I)

def ask(prompt):
    body = json.dumps({"model": "person", "prompt": prompt, "stream": False,
                       "options": {"num_predict": 1200}}).encode()
    r = urllib.request.urlopen(urllib.request.Request(ROUTER, body, {"Content-Type": "application/json"}), timeout=90)
    txt = json.loads(r.read())["response"]
    m = re.search(r"\[.*\]", txt, re.S)
    return json.loads(m.group(0)) if m else []

def ok(n):
    return (re.fullmatch(r"[A-Za-z]{3,12}", n) and not re.search(r"(.)\1\1", n.lower()) and not BAD.search(n))

def load():
    return set(l.strip() for l in open(OUT)) if os.path.exists(OUT) else set()

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--n", type=int, default=3000)
    sub.add_parser("check")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    names = load()
    if a.cmd == "generate":
        tries = 0
        while len(names) < a.n and tries < a.n // 20:
            tries += 1
            style = random.choice(STYLES)
            try:
                got = ask(PROMPT.format(n=60, style=style))
            except Exception as e:
                print("fail", e, file=sys.stderr); continue
            before = len(names)
            names |= {n.strip().capitalize() for n in got if isinstance(n, str) and ok(n.strip())}
            print(f"{len(names)} (+{len(names)-before}) {style[:40]}", flush=True)
            with open(OUT, "w") as fh: fh.write("\n".join(sorted(names)) + "\n")
    print(len(names), "names;", ", ".join(random.sample(sorted(names), min(25, len(names)))))

if __name__ == "__main__":
    main()
