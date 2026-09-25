"""Morphe-Automation unified tool: audit|note|join|prune (own implementation)."""
import argparse
import json
import re
import subprocess
from pathlib import Path


def audit_updates(force=False):
    from src.fetcher import REGISTRY  # noqa
    import src.adapters.archive_adapter  # noqa
    import src.adapters.apkmirror_adapter  # noqa
    from src.downloader import github_release

    unified = json.loads(Path("unified.json").read_text())
    try:
        manifest = json.loads(Path("manifest.json").read_text())
    except Exception:
        manifest = {}
    entries = manifest.get("entries", {})
    tags = {}
    matrix, carry, total = [], 0, 0
    for app in unified.get("apps", []):
        for arch in app.get("arches", ["universal"]):
            for mode in app.get("build_modes", ["apk"]):
                total += 1
                key = f"{app['app_name']}|{app['source']}|{arch}|{mode}"
                if force:
                    matrix.append({"app_name": app["app_name"], "source": app["source"], "arch": arch, "mode": mode})
                    continue
                src = app["source"]
                if src not in tags:
                    try:
                        sp = json.loads((Path("sources") / f"{src}.json").read_text())
                        entry = sp[2] if len(sp) > 2 else sp[1]
                        rel = github_release(entry["user"], entry["repo"], entry.get("tag", "latest"))
                        tags[src] = rel.get("tag_name", "")
                    except Exception:
                        tags[src] = ""
                old = entries.get(key, {})
                if not old or old.get("patches_tag") != tags.get(src, ""):
                    matrix.append({"app_name": app["app_name"], "source": app["source"], "arch": arch, "mode": mode})
                else:
                    carry += 1
    Path("build_matrix.json").write_text(json.dumps(matrix))
    import os

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"has_updates={'true' if matrix else 'false'}\n")
            f.write(f"build_matrix={json.dumps(matrix)}\n")
            f.write(f"update_count={len(matrix)}\n")
            f.write(f"total_count={total}\n")
            f.write(f"carry_count={carry}\n")
    print(f"audit: total={total} rebuild={len(matrix)} carry={carry}")


def note_build():
    import os

    apk = os.environ.get("APK_PATH", "")
    if not apk:
        cands = sorted(Path(".").glob("*-morphe-*.apk")) + sorted(Path("build").glob("*.zip"))
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
    print(f"noted {p.name}")


def join_manifest():
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
        entries[f"{r.get('app_name')}|{r.get('source')}|{r.get('arch')}|{r.get('mode')}"] = r
    Path("manifest.json").write_text(json.dumps({"entries": entries}, indent=2))
    print(f"joined manifest: {len(entries)}")


def prune_release(release, keep_file):
    try:
        keep = {x.strip() for x in open(keep_file) if x.strip()}
    except Exception:
        keep = set()

    def prefix(n):
        m = re.match(r"(.+-[^-]+-morphe)(?:-module)?-v", n)
        return m.group(1) if m else None

    keep_p = {prefix(k) for k in keep if prefix(k)}
    try:
        out = subprocess.check_output(["gh", "release", "view", release, "--json", "assets", "--jq", ".assets[].name"], text=True)
    except Exception as e:
        print(f"list failed: {e}")
        return
    for a in [x.strip() for x in out.splitlines() if x.strip()]:
        p = prefix(a)
        if p and p in keep_p and a not in keep:
            print(f"prune {a}")
            subprocess.run(["gh", "release", "delete-asset", release, a, "-y"], check=False)


def main():
    ap = argparse.ArgumentParser(prog="tool.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("audit")
    c.add_argument("--force", action="store_true")
    sub.add_parser("note")
    sub.add_parser("join")
    pr = sub.add_parser("prune")
    pr.add_argument("--release", default="latest")
    pr.add_argument("--keep-file", default="keep.txt")
    args = ap.parse_args()
    if args.cmd == "audit":
        audit_updates(force=args.force)
    elif args.cmd == "note":
        note_build()
    elif args.cmd == "join":
        join_manifest()
    elif args.cmd == "prune":
        prune_release(args.release, args.keep_file)


if __name__ == "__main__":
    main()
