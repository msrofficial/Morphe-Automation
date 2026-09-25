"""Legacy shim -> tools.tool note."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.tool import note_build

if __name__ == "__main__":
    note_build()
