"""v2 patch planner: own rule engine (Phase 3)."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatchRequest:
    cli: str
    patches: str
    package: str = ""
    build_mode: str = "apk"  # apk | module
    extra_args: str = ""


def read_rules(app_name: str, source: str):
    include, exclude = [], []
    p = Path("patches") / f"{app_name}-{source}.txt"
    if p.exists():
        for line in p.read_text().splitlines():
            s = line.strip()
            if s.startswith("-") and len(s) > 1:
                exclude += ["-d", s[1:].strip()]
            elif s.startswith("+") and len(s) > 1:
                include += ["-e", s[1:].strip()]
    return include, exclude


def find_special_patches(cli: str, bundle: str):
    """Return (microg_patch, branding_patch). Own parser, own names."""
    from src import utils

    out = utils.run_process(
        ["java", "-jar", cli, "list-patches", "--with-packages", bundle],
        capture=True,
        silent=True,
        check=False,
    ) or ""
    microg = branding = ""
    for line in out.splitlines():
        if not line.startswith("Name:"):
            continue
        title = line.split(":", 1)[1].strip()
        low = title.lower()
        if "microg" in low or "gmscore" in low:
            microg = title
        if "custom branding" in low:
            branding = title
    return microg, branding


def patch_command(req: PatchRequest, stock: Path, out: Path, include: list, exclude: list):
    cmd = ["java", "-jar", req.cli, "patch", "--patches", req.patches, "--out", str(out), str(stock)]
    cmd += include + exclude
    if req.extra_args:
        cmd += req.extra_args.split()
    return cmd
