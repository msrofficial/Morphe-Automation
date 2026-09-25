"""v2 module packager: own writer (Phase 3). Replaces module_builder."""
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from src import utils

TEMPLATE_DIR = Path("module")


def _device_arch(arch: str) -> str:
    return {"arm64-v8a": "arm64", "arm-v7a": "arm"}.get(arch, "")


def write_device_config(dest: Path, package: str, version: str, arch: str):
    dest.write_text(f"PKG_NAME={package}\nPKG_VER={version}\nMODULE_ARCH={_device_arch(arch)}\n")


def write_module_prop(dest: Path, prop_id: str, label: str, version: str, update_file: str):
    code = os.environ.get("NEXT_VER_CODE") or datetime.now().strftime("%Y%m%d")
    repo = os.environ.get("GITHUB_REPOSITORY", "msrofficial/Morphe-Automation")
    dest.write_text(
        f"id={prop_id}\nname={label}\nversion=v{version}\nversionCode={code}\n"
        f"author=msrofficial\ndescription={label} module\n"
        f"updateJson=https://raw.githubusercontent.com/{repo}/update/{update_file}\n"
    )


def package_module(patched_apk: Path, app_name: str, arch: str, version: str, app_cfg: dict, package: str) -> str:
    out_dir = Path("build")
    out_dir.mkdir(exist_ok=True)
    work = Path(f"temp/pkg-{app_name}-{arch}")
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(TEMPLATE_DIR, work)
    write_device_config(work / "config", package, version, arch)
    prop_id = app_cfg.get("module_prop_name") or f"{app_name}-morphe"
    label = f"{app_name} Morphe"
    write_module_prop(work / "module.prop", prop_id, label, version, f"{app_name}-update.json")
    shutil.copyfile(work / "module.prop", work / "module.prop.orig")
    apk = Path(patched_apk)
    utils.strip_zip_entries(apk, ["lib/*"])
    shutil.copyfile(apk, work / "base.apk")
    if app_cfg.get("include_stock", "merged") != "disable":
        (work / "stock").mkdir(exist_ok=True)
        stocks = sorted(Path("temp").glob(f"{package}-*.apk")) + sorted(Path(".").glob(f"{package}-*.apk"))
        stocks += sorted(Path(".").glob(f"{app_name}-stock-*.apk"))
        if stocks:
            shutil.copyfile(stocks[-1], work / "stock" / "base.apk")
    level = 9
    try:
        level = max(0, min(9, int(app_cfg.get("compression-level", 9))))
    except Exception:
        pass
    out = out_dir / f"{app_name}-morphe-module-v{version}-{arch}.zip"
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=level) as z:
        for p in sorted(work.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(work))
    shutil.rmtree(work, ignore_errors=True)
    Path(patched_apk).unlink(missing_ok=True)
    logging.info(f"packaged module: {out}")
    return str(out)
