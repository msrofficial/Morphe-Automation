"""Merge build_records into manifest.json (apk + module)."""
import json
from pathlib import Path


def main():
    base = {}
    if Path("new_manifest.json").exists():
        try:
            base = json.loads(Path("new_manifest.json").read_text())
        except Exception:
            base = {}
    entries = base.get("entries", {})
    for f in Path("build_records").glob("*.json"):
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        key = f"{r.get('app_name')}|{r.get('source')}|{r.get('arch')}|{r.get('mode')}"
        entries[key] = r
    Path("manifest.json").write_text(json.dumps({"entries": entries}, indent=2))
    print(f"manifest entries: {len(entries)}")


if __name__ == "__main__":
    main()
