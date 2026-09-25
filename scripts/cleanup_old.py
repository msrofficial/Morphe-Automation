"""Legacy shim -> tools.tool prune."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.tool import prune_release
import argparse

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="latest")
    ap.add_argument("--keep-file", default="keep.txt")
    a = ap.parse_args()
    prune_release(a.release, a.keep_file)
