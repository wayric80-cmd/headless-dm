#!/usr/bin/env python3
"""Read-only saved-DB equipment snapshot; use paired cohorts after regear."""
from pathlib import Path
import collections
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
query = """SELECT c.guid,c.level,ci.slot,t.Quality,ii.itemEntry,IF(r.guid IS NULL,0,1)
FROM characters c JOIN acore_auth.account a ON a.id=c.account
LEFT JOIN character_inventory ci ON ci.guid=c.guid AND ci.bag=0 AND ci.slot<19 AND ci.slot NOT IN (3,18)
LEFT JOIN item_instance ii ON ii.guid=ci.item
LEFT JOIN acore_world.item_template t ON t.entry=ii.itemEntry
LEFT JOIN wov_regear_bracket r ON r.guid=c.guid AND r.bracket=LEAST(c.level,60) DIV 10
WHERE a.username LIKE 'RNDBOT%' AND c.level>=30 ORDER BY c.guid,ci.slot"""
r = subprocess.run(["bash","-c",'. ops/env.sh; db acore_characters --batch --skip-column-names -e "$1"',"gear-report",query],cwd=root,text=True,capture_output=True,check=True)
characters = {}
for line in r.stdout.splitlines():
    guid,level,slot,quality,entry,regeared = line.split("\t")
    row = characters.setdefault(guid,{"level":int(level),"regeared":bool(int(regeared)),"slots":{}})
    if slot != "NULL": row["slots"][slot] = {"quality":None if quality=="NULL" else int(quality),"entry":None if entry=="NULL" else int(entry)}
summary = collections.defaultdict(lambda:{"characters":0,"equipped":0,"grey_white":0,"rare":0,"epic":0,"missing_core":0})
for c in characters.values():
    band=str(min(c["level"],60)//10*10)
    s=summary[band]
    s["characters"]+=1
    for slot,item in c["slots"].items():
        s["equipped"]+=1
        q=item["quality"]
        s["grey_white"]+=q is not None and q<2
        s["rare"]+=q==3
        s["epic"]+=q==4
    required=[0,1,2,4,5,6,7,8,9,10,11,14,15]
    if c["level"]>=50: required.extend([12,13])
    s["missing_core"]+=sum(str(slot) not in c["slots"] for slot in required)
result={"basis":"saved DB, not live client equipment","characters":characters,"summary":dict(summary)}
if len(sys.argv)>1: Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result["summary"],indent=2))
