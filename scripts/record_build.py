"""Record a built APK/module into build_records/ for manifest merge."""
import json
import os
import re
from pathlib import Path


def main():
    apk = os.environ.get("APK_PATH", "")
    if not apk:
        # fallback: find newest apk/zip
        cands = sorted(Path(".").glob("*.apk")) + sorted(Path(".").glob("*-module-*.zip"))
        if not cands:
            return
        apk = str(cands[-1])
    p = Path(apk)
    m = re.match(r"(.+)-([^-]+)-morphe(?:-module)?-v(.+)\.(\w+)", p.stem)
    rec = {"file": p.name}
    if m:
        rec.update({"app": m.group(1), "arch": m.group(2), "version": m.group(3)})
    rec["app_name"] = os.environ.get("APP_NAME", rec.get("app", ""))
    rec["source"] = os.environ.get("SOURCE", "")
    rec["arch"] = os.environ.get("ARCH", rec.get("arch", ""))
    rec["mode"] = os.environ.get("MODE", "apk")
    Path("build_records").mkdir(exist_ok=True)
    (Path("build_records") / f"{p.stem}.json").write_text(json.dumps(rec, indent=2))
    print(f"recorded {p.name}")


if __name__ == "__main__":
    main()
