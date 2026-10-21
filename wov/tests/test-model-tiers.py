from pathlib import Path
import tomllib
root = Path(__file__).resolve().parents[2]
cfg = tomllib.loads((root / "site/fleet.toml").read_text())
assert cfg["routes"]["ambient"] == ["haiku", "main"]
assert cfg["routes"]["person"] == ["haiku", "main"]
assert cfg["routes"]["premium"] == ["sonnet", "haiku", "main"]
assert cfg["backends"]["sonnet"]["model"] == "claude-sonnet-5-5"
assert cfg["backends"]["haiku"]["model"] == "claude-haiku-5-5"
assert cfg["backends"]["sonnet"]["api_key_env"] == cfg["backends"]["haiku"]["api_key_env"]
assert cfg["backends"]["sonnet"]["router_slots"] == 2
for route, chain in cfg["routes"].items():
    assert chain and len(chain) == len(set(chain)), route
    assert all(name in cfg["backends"] for name in chain), route
assert all("api_key" not in backend for backend in cfg["backends"].values())
print("Model route and fallback checks passed (no credentials accessed)")

# The installer preserves unrelated local settings and is idempotent.
import importlib.util
spec = importlib.util.spec_from_file_location("wov_model_installer", root / "wov/apply-model-tiers.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
fragment = (root / "wov/conf/model-tiers.fleet.toml").read_text()
base = '[backends.main]\nurl="http://localhost:8080"\nmodel="local"\n[backends.haiku]\nurl="https://api.anthropic.com/v1"\nmodel="claude-haiku-5-5"\napi_key_env="TEST_KEY_NAME"\n[routes]\nambient=["main"]\nutility=["main"]\n'
merged = installer.apply_text(base, fragment)
parsed = tomllib.loads(merged)
assert parsed["routes"]["utility"] == ["main"]
assert parsed["backends"]["haiku"]["api_key_env"] == "TEST_KEY_NAME"
assert parsed["routes"]["premium"] == ["sonnet", "haiku", "main"]
assert installer.apply_text(merged, fragment) == merged
print("Model installer preservation/idempotence checks passed")

try:
    installer.apply_text('[routes]\nambient=["haiku","main"]\n', fragment)
except ValueError:
    pass
else:
    raise AssertionError("Missing backend must be rejected before writing")
print("Missing-backend safety check passed")
