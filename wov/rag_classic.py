#!/usr/bin/env python3
"""Way of Vanilla: install mod-ollama-chat RAG (player voice) trimmed to Classic.

Deterministic, no model calls. Entries whose title is later-era are dropped; in
other entries, sentences naming later-era content are removed, as are keywords
and tags naming it. Usage: rag_classic.py SRC DST [--dry-run]
"""
import json, glob, os, re, sys
sys.path.insert(0, "/opt/wow/headless-dm/services/lore")
import era
EXTRA = (r"death ?knights?|\bDK\b|arenas?|achievements?|glyphs?|emblems?|heroic|dungeon finder|\bLFD\b|\bRDF\b|"
         r"level (?:6[1-9]|7\d|80)|\b(?:6[1-9]|7\d|80)\b|wrath|burning crusade|\bTBC\b|\bBC\b|flying mounts?|"
         r"cold weather flying|dual spec|jewelcraft\w*|inscription|vehicle|wintergrasp|barbershop|lich king")
PAT = re.compile("(?:" + era.ERAS["classic"]["meta_extra"] + "|" + EXTRA + ")", re.I)
SENT = re.compile(r"(?<=[.!?])\s+")
src, dst = sys.argv[1], sys.argv[2]
dry = "--dry-run" in sys.argv
stats = {"kept": 0, "trimmed": 0, "dropped": 0}
out, dropped = {}, []
for f in sorted(glob.glob(os.path.join(src, "*.json"))):
    res = []
    for x in json.load(open(f, encoding="utf-8")):
        if PAT.search(x["title"]):
            stats["dropped"] += 1; dropped.append(x["title"]); continue
        sents = SENT.split(x["content"].strip())
        good = [s for s in sents if not PAT.search(s)]
        if len(good) < len(sents):
            if len(" ".join(good).split()) < 20:
                stats["dropped"] += 1; dropped.append(x["title"]); continue
            stats["trimmed"] += 1
        else:
            stats["kept"] += 1
        x = dict(x, content=" ".join(good),
                 keywords=[k for k in x.get("keywords", []) if not PAT.search(k)],
                 tags=[t for t in x.get("tags", []) if not PAT.search(t)])
        assert not PAT.search(x["title"] + " " + x["content"])
        res.append(x)
    out[os.path.basename(f)] = res
print(stats)
print("dropped:", "; ".join(dropped))
if not dry:
    os.makedirs(dst, mode=0o755, exist_ok=True)
    for name, res in out.items():
        with open(os.path.join(dst, name), "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
    print("wrote", len(out), "files to", dst)
