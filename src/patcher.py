"""Build morphe patch command with j-hc extras (microg/branding/exclusive)."""
import logging
from pathlib import Path
from src import utils


def read_patch_rules(app_name: str, source: str):
    inc, exc = [], []
    p = Path("patches") / f"{app_name}-{source}.txt"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line.startswith("-") and len(line) > 1:
                exc += ["-d", line[1:].strip()]
            elif line.startswith("+") and len(line) > 1:
                inc += ["-e", line[1:].strip()]
    return inc, exc


def detect_microg_branding(cli: str, patches: str, package: str):
    """Return (microg_patch, branding_patch) names or empty strings."""
    out = utils.run_process(
        ["java", "-jar", cli, "list-patches", "--with-packages", patches],
        capture=True,
        silent=True,
        check=False,
    ) or ""
    microg, branding = "", ""
    for line in out.splitlines():
        low = line.lower()
        if package.lower() not in low:
            # list-patches output groups by patch; check Name lines
            pass
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip()
            if "microg" in name.lower() or "gmscore" in name.lower():
                microg = name
            if "custom branding" in name.lower():
                branding = name
    return microg, branding


def build_command(cli, patches, inp, out, inc, exc, extra_args="", build_mode="apk"):
    cmd = ["java", "-jar", str(cli), "patch", "--patches", str(patches), "--out", str(out), str(inp)]
    cmd += inc + exc
    if extra_args:
        cmd += extra_args.split()
    return cmd
