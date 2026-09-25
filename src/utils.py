"""Shared utilities: versions, files, signing, integrity, signatures."""
import json
import logging
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional


def run_process(command, cwd=None, capture=False, silent=False, check=True):
    proc = subprocess.Popen(
        [str(c) for c in command],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    out_lines = []
    try:
        for line in iter(proc.stdout.readline, ""):
            if line:
                if not silent:
                    print(line.rstrip(), flush=True)
                if capture:
                    out_lines.append(line)
        proc.stdout.close()
        rc = proc.wait()
        output = "".join(out_lines).strip() if capture else None
        if check and rc != 0:
            raise subprocess.CalledProcessError(rc, command, output=output)
        return output
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass


def find_file(files, suffix=None, contains=None, exclude=None):
    exclude = exclude or []
    for f in files:
        name = f.name.lower()
        if any(e.lower() in name for e in exclude):
            continue
        if suffix and not name.endswith(suffix):
            continue
        if contains and contains.lower() not in name:
            continue
        return f
    if exclude:
        for f in files:
            name = f.name.lower()
            if suffix and not name.endswith(suffix):
                continue
            if contains and contains.lower() not in name:
                continue
            return f
    return None


def find_apksigner():
    on_path = shutil.which("apksigner")
    if on_path:
        return on_path
    for root in [
        "/usr/local/lib/android/sdk",
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
    ]:
        if not root:
            continue
        bt = Path(root) / "build-tools"
        if not bt.exists():
            continue
        for ver in sorted(bt.iterdir(), reverse=True):
            p = ver / "apksigner"
            if p.is_file():
                return str(p)
    # fallback to bundled jar handled by caller
    return None


def normalize_version(version: str):
    parts = version.split(".")
    norm = []
    for part in parts:
        m = re.match(r"(\d+)", part)
        norm.append(int(m.group(1)) if m else 0)
    bm = re.search(r"build\s+(\d+)", version, re.IGNORECASE)
    if bm:
        norm.append(int(bm.group(1)))
    pm = re.search(r"\((\d+)\)$", version)
    if pm:
        norm.append(int(pm.group(1)))
    return norm


def get_highest_version(versions):
    if not versions:
        return None
    best = versions[0]
    for v in versions[1:]:
        if normalize_version(v) > normalize_version(best):
            best = v
    return best


def get_supported_versions(package_name: str, cli: str, patches: str):
    """Ask morphe/revanced CLI for compatible versions, highest first."""
    cli_name = Path(cli).name.lower()
    is_morphe = "morphe" in cli_name
    if is_morphe:
        cmd = ["java", "-jar", cli, "list-versions", "-f", package_name, "--patches", patches]
    elif "revanced-cli-6" in cli_name or "revanced-cli-7" in cli_name or "revanced-cli-8" in cli_name:
        cmd = ["java", "-jar", cli, "list-versions", "-p", patches, "-b", "-f", package_name]
    else:
        cmd = ["java", "-jar", cli, "list-versions", "-f", package_name, patches]
    output = run_process(cmd, capture=True, silent=True, check=False)
    if not output:
        return []
    lines = output.splitlines()
    if not lines or len(lines) <= 2:
        return []
    first = lines[0].strip().lower()
    if "usage:" in first or "unmatched argument" in first or "error" in first:
        return []
    versions = []
    for line in lines[2:]:
        line = line.strip()
        if not line or "Any" in line:
            continue
        parts = line.split()
        if not parts or not parts[0][0].isdigit():
            continue
        ver = parts[0]
        if len(parts) >= 3 and parts[1].lower() == "build":
            ver = f"{parts[0]} build {parts[2]}"
        versions.append(ver)
    versions = sorted(set(versions), key=normalize_version, reverse=True)
    return versions


def strip_zip_entries(zip_path: Path, patterns):
    if not zip_path or not zip_path.exists():
        return
    if shutil.which("zip"):
        try:
            run_process(["zip", "--delete", str(zip_path)] + list(patterns), silent=True, check=False)
            return
        except Exception:
            pass
    import fnmatch

    tmp = zip_path.with_suffix(".tmp.zip")
    try:
        with zipfile.ZipFile(zip_path, "r") as zin:
            with zipfile.ZipFile(tmp, "w", compression=zin.compression) as zout:
                for item in zin.infolist():
                    if any(fnmatch.fnmatch(item.filename, p) for p in patterns):
                        continue
                    zout.writestr(item, zin.read(item.filename))
        tmp.replace(zip_path)
    except Exception as e:
        logging.debug(f"strip failed: {e}")
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def check_apk_integrity(apk_path: Path) -> bool:
    if not apk_path or not apk_path.exists() or apk_path.stat().st_size == 0:
        return False
    try:
        if not zipfile.is_zipfile(apk_path):
            return False
        with zipfile.ZipFile(apk_path, "r") as z:
            return z.testzip() is None
    except Exception:
        return False


def check_sig(apksigner_jar: Optional[str], apk: Path, pkg: str, sig_file: Path = Path("sig.txt")) -> bool:
    """Return True if signature matches whitelist or no whitelist entry."""
    if not sig_file.exists():
        return True
    text = sig_file.read_text(errors="ignore")
    if pkg not in text:
        return True
    # need apksigner verify
    cmd = None
    if apksigner_jar and Path(apksigner_jar).exists():
        cmd = ["java", "-jar", apksigner_jar, "verify", "--print-certs", str(apk)]
    else:
        finder = find_apksigner()
        if finder:
            cmd = [finder, "verify", "--print-certs", str(apk)]
        else:
            logging.warning("no apksigner for sig check, skipping")
            return True
    out = run_process(cmd, capture=True, silent=True, check=False) or ""
    sig = None
    for line in out.splitlines():
        if "SHA-256" in line and "Signer" in line:
            sig = line.strip().split()[-1]
    if not sig:
        return False
    return f"{sig} {pkg}" in [l.strip() for l in text.splitlines()]


def load_unified(path: Path = Path("unified.json")):
    with path.open() as f:
        data = json.load(f)
    # dedup apps with same (app_name, source)
    seen = set()
    apps = []
    for a in data.get("apps", []):
        key = (a.get("app_name"), a.get("source"))
        if key in seen:
            continue
        seen.add(key)
        apps.append(a)
    data["apps"] = apps
    return data
