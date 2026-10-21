#!/usr/bin/env python3
"""Way of Vanilla: apply wov/conf/*.wov.overrides on top of the live configs.

Run AFTER HeadlessDM's ops/scripts/conf-apply.py (which would otherwise put its own values back).
    python3 wov/apply-overlay.py [--dry-run]
Backs each changed live conf up beside it with a timestamp. Prints how many keys changed.
"""
import datetime as dt, glob, os, re, shutil, sys
HERE = os.path.dirname(os.path.realpath(__file__))
ETC = "/opt/wow/server/etc"
LINE = re.compile(r"^\s*([A-Za-z0-9_.]+)\s*=\s*(.*?)\s*$")
dry = "--dry-run" in sys.argv
for ov in sorted(glob.glob(os.path.join(HERE, "conf", "*.wov.overrides"))):
    name = os.path.basename(ov)[: -len(".wov.overrides")]
    live = next((p for p in (os.path.join(ETC, "modules", name + ".conf"), os.path.join(ETC, name + ".conf"))
                 if os.path.exists(p)), None)
    if not live:
        sys.exit(f"{name}: live conf not found")
    want = {}
    for l in open(ov, encoding="utf-8"):
        m = LINE.match(l)
        if m and not l.lstrip().startswith("#"):
            want[m.group(1)] = m.group(2)
    lines = open(live, encoding="utf-8").read().split("\n")
    seen, changed = set(), 0
    for i, l in enumerate(lines):
        m = LINE.match(l)
        if m and not l.lstrip().startswith("#") and m.group(1) in want:
            k = m.group(1); seen.add(k)
            new = f"{k} = {want[k]}"
            if l != new:
                lines[i] = new; changed += 1
    for k, v in want.items():
        if k not in seen:
            lines.append(f"{k} = {v}"); changed += 1
    print(f"{name}: {changed} key(s) changed of {len(want)}")
    if changed and not dry:
        shutil.copy2(live, f"{live}.bak-wov-{dt.datetime.now():%Y%m%d-%H%M%S}")
        open(live, "w", encoding="utf-8").write("\n".join(lines))

# Keep the managed model routes reproducible alongside the config overlays.
import subprocess
subprocess.run([sys.executable, os.path.join(HERE, "apply-model-tiers.py")] +
               (["--dry-run"] if dry else []), check=True)
