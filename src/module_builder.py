"""Build Magisk module zip from patched APK (j-hc logic ported)."""
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from src import utils

TEMPLATE = Path("module")


def _arch_code(arch: str) -> str:
    if arch == "arm64-v8a":
        return "arm64"
    if arch == "arm-v7a":
        return "arm"
    return ""


def build_module(patched_apk: Path, app_name: str, source: str, arch: str, version: str, app_cfg: dict, pkg: str):
    build_dir = Path("build")
    build_dir.mkdir(exist_ok=True)
    tmp = Path(f"temp/mod-{app_name}-{arch}")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(TEMPLATE, tmp)
    # config file for on-device scripts
    (tmp / "config").write_text(f"PKG_NAME={pkg}\nPKG_VER={version}\nMODULE_ARCH={_arch_code(arch)}\n")
    # module.prop
    ver_code = os.environ.get("NEXT_VER_CODE") or datetime.now().strftime("%Y%m%d")
    prop_name = app_cfg.get("module_prop_name") or f"{app_name}-morphe"
    display = f"{app_name} Morphe"
    update_json = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', 'msrofficial/Morphe-Automation')}/update/{app_name}-update.json"
    prop = (
        f"id={prop_name}\nname={display}\nversion=v{version}\nversionCode={ver_code}\n"
        f"author=msrofficial\ndescription={display} module\nupdateJson={update_json}\n"
    )
    (tmp / "module.prop").write_text(prop)
    (tmp / "module.prop.orig").write_text(prop)
    # base apk: strip all libs for module (stock provides libs)
    patched = Path(patched_apk)
    utils.strip_zip_entries(patched, ["lib/*"])
    shutil.copyfile(patched, tmp / "base.apk")
    # stock include
    mode = app_cfg.get("include_stock", "merged")
    if mode != "disable":
        (tmp / "stock").mkdir(exist_ok=True)
        # stock apk path recorded by caller via env? find latest stock in temp
        stocks = sorted(Path("temp").glob(f"{pkg}-*.apk"))
        if stocks:
            shutil.copyfile(stocks[-1], tmp / "stock" / "base.apk")
    # cleanup device-only bins not needed in zip? keep all, on-device script cleans
    for d in (tmp / "bin").glob("*/tmp.*"):
        d.unlink(missing_ok=True)
    level = int(app_cfg.get("compression-level", 9)) if isinstance(app_cfg, dict) else 9
    out_name = f"{app_name}-morphe-module-v{version}-{arch}.zip"
    out = build_dir / out_name
    # python zipfile compresslevel 0-9
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=max(0, min(9, level))) as z:
        for p in sorted(tmp.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(tmp))
    shutil.rmtree(tmp, ignore_errors=True)
    Path(patched_apk).unlink(missing_ok=True)
    logging.info(f"module built: {out}")
    return str(out)
