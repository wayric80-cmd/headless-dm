#!/usr/bin/env python3
"""Uppdatera wov/HANDOVER.md.
  note.py log "text"        lägger till en rad under ## Logg (med tid)
  note.py now "text"        ersätter innehållet under ## Pågående arbete (text får ha radbrytningar; '-' = läs stdin)
  note.py done N            bockar av punkt N under ## Att göra
"""
import sys, re, datetime, pathlib
p = pathlib.Path(__file__).with_name("HANDOVER.md"); s = p.read_text()
cmd, arg = sys.argv[1], (sys.stdin.read() if sys.argv[2] == "-" else sys.argv[2])
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
if cmd == "log":
    s = s.rstrip("\n") + f"\n- {ts} {arg.strip()}\n"
elif cmd == "now":
    s = re.sub(r"(## Pågående arbete\n).*?(\n## Logg)", lambda m: m.group(1) + f"(uppdaterad {ts})\n" + arg.strip() + "\n" + m.group(2), s, flags=re.S)
elif cmd == "done":
    s = re.sub(rf"^({re.escape(arg)}\. )\[ \]", r"\1[x]", s, count=1, flags=re.M)
p.write_text(s); print("ok")
