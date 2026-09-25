"""Legacy shim -> tools.tool join."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.tool import join_manifest

if __name__ == "__main__":
    join_manifest()
