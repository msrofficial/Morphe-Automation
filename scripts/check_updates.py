"""Legacy shim -> tools.tool audit (keeps old workflow working)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.tool import audit_updates
import os

if __name__ == "__main__":
    audit_updates(force=os.environ.get("FORCE_FULL_REBUILD", "false").lower() == "true")
