"""Check for updates: compare morphe patches tag + app versions vs manifest."""
import json
import os
from pathlib import Path

from src.downloader import github_release


def main():
    unified = json.loads(Path("unified.json").read_text())
    manifest = {}
    if Path("manifest.json").exists():
        try:
            manifest = json.loads(Path("manifest.json").read_text())
        except Exception:
            manifest = {}
    entries = manifest.get("entries", {})

    force = os.environ.get("FORCE_FULL_REBUILD", "false").lower() == "true"
    matrix, carry = [], 0
    total = 0
    # cache patches tags per source
    tag_cache = {}
    for app in unified["apps"]:
        for arch in app.get("arches", ["universal"]):
            for mode in app.get("build_modes", ["apk"]):
                total += 1
                key = f"{app['app_name']}|{app['source']}|{arch}|{mode}"
                if force:
                    matrix.append({"app_name": app["app_name"], "source": app["source"], "arch": arch, "mode": mode})
                    continue
                src = app["source"]
                if src not in tag_cache:
                    try:
                        sp = json.loads((Path("sources") / f"{src}.json").read_text())
                        # second entry is patches repo
                        patches_entry = sp[2] if len(sp) > 2 else sp[1]
                        rel = github_release(patches_entry["user"], patches_entry["repo"], patches_entry.get("tag", "latest"))
                        tag_cache[src] = rel.get("tag_name", "")
                    except Exception:
                        tag_cache[src] = ""
                old = entries.get(key, {})
                if not old or old.get("patches_tag") != tag_cache.get(src, ""):
                    matrix.append({"app_name": app["app_name"], "source": app["source"], "arch": arch, "mode": mode})
                else:
                    carry += 1

    out_has = "true" if matrix else "false"
    print(f"total={total} rebuild={len(matrix)} carry={carry}")
    Path("build_matrix.json").write_text(json.dumps(matrix))
    # github outputs
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"has_updates={out_has}\n")
            f.write(f"build_matrix={json.dumps(matrix)}\n")
            f.write(f"update_count={len(matrix)}\n")
            f.write(f"total_count={total}\n")
            f.write(f"carry_count={carry}\n")


if __name__ == "__main__":
    main()
