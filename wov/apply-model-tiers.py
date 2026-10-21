#!/usr/bin/env python3
"""Apply tracked WoV model settings to the ignored site/fleet.toml; no credential access."""
import datetime
import json
from pathlib import Path
import re
import shutil
import sys
import tomllib

HERE = Path(__file__).resolve().parent

def section(text, name):
    pattern = re.compile(r"^\[" + re.escape(name) + r"\][^\S\n]*\n.*?(?=^\[|\Z)", re.M | re.S)
    return pattern, pattern.search(text)

def apply_text(text, fragment):
    current = tomllib.loads(text)
    wanted = tomllib.loads(fragment)
    available = set(current.get("backends", {})) | {"sonnet"}
    if any(name not in available for chain in wanted["routes"].values() for name in chain):
        raise ValueError("Configure the existing Haiku/local backends before applying model tiers")
    if (current.get("backends", {}).get("sonnet") == wanted["backends"]["sonnet"] and
        all(current.get("routes", {}).get(k) == v for k, v in wanted["routes"].items())):
        return text
    _, match = section(fragment, "backends.sonnet")
    if not match:
        raise ValueError("Missing managed Sonnet section")
    block = match.group(0).rstrip() + "\n\n"
    pattern, existing = section(text, "backends.sonnet")
    text = pattern.sub(lambda _: block, text, count=1) if existing else text.rstrip() + "\n\n" + block
    pattern, existing = section(text, "routes")
    routes = existing.group(0) if existing else "[routes]\n"
    for key, value in wanted["routes"].items():
        line = key + " = " + json.dumps(value) + "\n"
        key_pattern = re.compile(r"^" + re.escape(key) + r"\s*=.*(?:\n|$)", re.M)
        routes = key_pattern.sub(lambda _: line, routes, count=1) if key_pattern.search(routes) else routes.rstrip() + "\n" + line
    text = pattern.sub(lambda _: routes.rstrip() + "\n\n", text, count=1) if existing else text.rstrip() + "\n\n" + routes
    parsed = tomllib.loads(text)
    for chain in wanted["routes"].values():
        if not all(name in parsed.get("backends", {}) for name in chain):
            raise ValueError("Managed route references a missing backend")
    return text

def main():
    path = HERE.parent / "site/fleet.toml"
    text = path.read_text()
    updated = apply_text(text, (HERE / "conf/model-tiers.fleet.toml").read_text())
    if text == updated:
        print("model tiers: fleet already matches")
        return
    if "--dry-run" in sys.argv:
        print("model tiers: fleet update required (dry run)")
        return
    backup = Path("/opt/wow/backups") / ("fleet-model-tiers-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".toml")
    shutil.copy2(path, backup)
    path.write_text(updated)
    print("model tiers: fleet updated; backup:", backup)

if __name__ == "__main__":
    main()
