"""Delete superseded old-version APKs/modules from a release."""
import argparse
import re
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="latest")
    ap.add_argument("--keep-file", default="keep.txt")
    args = ap.parse_args()
    try:
        keep = set(x.strip() for x in open(args.keep_file) if x.strip())
    except Exception:
        keep = set()
    # list release assets
    try:
        out = subprocess.check_output(["gh", "release", "view", args.release, "--json", "assets", "--jq", ".assets[].name"], text=True)
    except Exception as e:
        print(f"list failed: {e}")
        return
    assets = [a.strip() for a in out.splitlines() if a.strip()]
    # group by app-arch prefix
    def prefix(n):
        m = re.match(r"(.+-[^-]+-morphe)(?:-module)?-v", n)
        return m.group(1) if m else None

    keep_prefix = {prefix(k) for k in keep if prefix(k)}
    for a in assets:
        p = prefix(a)
        if p and p in keep_prefix and a not in keep:
            print(f"delete old {a}")
            try:
                subprocess.run(["gh", "release", "delete-asset", args.release, a, "-y"], check=False)
            except Exception as e:
                print(f"delete failed {a}: {e}")


if __name__ == "__main__":
    main()
