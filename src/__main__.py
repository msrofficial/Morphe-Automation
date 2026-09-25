"""Main orchestrator: unified.json -> download -> patch -> apk/module."""
import json
import logging
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from os import getenv

from src import downloader, patcher, utils

try:
    import src.adapters.apkmirror_adapter  # noqa: F401 (self-register)
    import src.adapters.archive_adapter  # noqa: F401 (self-register)
    from src import fetcher as _v2fetch

    _V2 = True
except Exception:
    _V2 = False

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _should_retry(output):
    if not output:
        return False
    t = output.lower()
    return (
        "failed to match the fingerprint" in t
        or "patch.patchexception" in t
        or "patching aborted" in t
    )


def run_build(app_name, source, arch="universal", build_mode="apk", app_cfg=None):
    app_cfg = app_cfg or {}
    files, _name = downloader.download_required(source)
    cli = utils.find_file(files, suffix=".jar", contains="morphe-cli") or utils.find_file(files, suffix=".jar")
    patches = utils.find_file(files, suffix=".mpp") or utils.find_file(files, contains="patches", suffix=".jar")
    if not cli or not patches:
        logging.error(f"CLI/patches missing for {source}: {[f.name for f in files]}")
        return None

    order = ["archive", "apkmirror", "uptodown", "apkpure", "direct"]
    inp, version, cands = None, None, []
    used = None
    for plat in order:
        # v2 path first for archive/apkmirror, legacy fallback on error
        if _V2 and plat in ("archive", "apkmirror"):
            try:
                from src.downloader import _load_app_config

                cfg = _load_app_config(app_name, plat)
                if cfg and cfg.get("package"):
                    adapter = _v2fetch.get_adapter(plat)
                    pinned = (cfg.get("version") or "").strip()
                    if pinned:
                        tries = [pinned]
                    else:
                        tries = utils.get_supported_versions(cfg["package"], str(cli), str(patches))
                        try:
                            latest = adapter.latest(app_name, {**cfg, "arch": arch})
                            if latest and latest not in tries:
                                tries.append(latest)
                        except Exception:
                            pass
                    for ver in tries:
                        link = adapter.link(ver, app_name, {**cfg, "arch": arch})
                        if not link:
                            continue
                        dest = Path(f"{app_name}-stock-{plat}-{ver.replace(' ', '')}.apk")
                        _v2fetch.download_url(link, dest)
                        inp, version, cands = dest, ver, tries
                        used = getattr(downloader, f"download_{plat}", None)
                        break
                if inp:
                    break
            except Exception as e:
                logging.debug(f"v2 {plat} failed, legacy fallback: {e}")
        fn = getattr(downloader, f"download_{plat}", None)
        if not fn:
            continue
        inp, version, cands = fn(app_name, str(cli), str(patches), arch)
        if inp:
            used = fn
            break
    if not inp or not version:
        logging.error(f"download failed for {app_name}")
        return None

    # sig guard (j-hc)
    pkg = None
    for plat in order:
        cfgp = Path("apps") / plat / f"{app_name}.json"
        if cfgp.exists():
            try:
                pkg = json.loads(cfgp.read_text()).get("package")
                break
            except Exception:
                pass
    if pkg and not utils.check_sig("bin/apksigner.jar", inp, pkg):
        logging.warning(f"signature mismatch for {app_name}, continuing (archive source trusted)")
        # do not skip: archive.org stock may be re-signed; patcher will verify

    inc, exc = patcher.read_patch_rules(app_name, source)
    microg, branding = "", ""
    try:
        microg, branding = patcher.detect_microg_branding(str(cli), str(patches), pkg or "")
    except Exception as e:
        logging.debug(f"branding detect failed: {e}")
    if microg:
        if build_mode == "apk":
            inc += ["-e", microg]
        else:
            exc += ["-d", microg]
    if branding and build_mode == "module":
        exc += ["-d", branding]

    versions = [version] + [v for v in (cands or []) if v != version]
    for idx, ver in enumerate(versions):
        if idx > 0:
            logging.warning(f"retry {app_name} with {ver}")
            try:
                inp.unlink(missing_ok=True)
            except Exception:
                pass
            inp, version, _ = used(app_name, str(cli), str(patches), arch, override_version=ver)
            if not inp:
                continue
        # bundle merge
        if inp.suffix != ".apk":
            is_bundle = inp.suffix.lower() in [".apkm", ".xapk", ".apks", ".zip"]
            try:
                if zipfile.is_zipfile(inp):
                    with zipfile.ZipFile(inp) as z:
                        if any(n.endswith(".apk") for n in z.namelist()):
                            is_bundle = True
            except Exception:
                pass
            if is_bundle:
                editor = downloader.download_apkeditor()
                merged = inp.with_suffix(".apk")
                try:
                    utils.run_process(["java", "-jar", str(editor), "m", "-f", "-i", str(inp), "-o", str(merged)], silent=True)
                    inp.unlink(missing_ok=True)
                    inp = merged
                except Exception as e:
                    logging.warning(f"merge failed: {e}")
        # arch strip for apk; module strips all libs later
        if build_mode == "apk":
            if arch == "arm64-v8a":
                utils.strip_zip_entries(inp, ["lib/x86/*", "lib/x86_64/*", "lib/armeabi-v7a/*"])
            elif arch == "armeabi-v7a":
                utils.strip_zip_entries(inp, ["lib/x86/*", "lib/x86_64/*", "lib/arm64-v8a/*"])
            else:
                utils.strip_zip_entries(inp, ["lib/x86/*", "lib/x86_64/*"])
        if not utils.check_apk_integrity(inp):
            logging.error("bad apk integrity")
            return None
        out = Path(f"{app_name}-{arch}-patch-v{version}.apk")
        cmd = patcher.build_command(cli, patches, inp, out, inc, exc, app_cfg.get("patcher_args", ""), build_mode)
        logging.info(" ".join(cmd))
        try:
            utils.run_process(cmd, capture=True, stream=False)
        except subprocess.CalledProcessError as e:
            inp.unlink(missing_ok=True)
            out.unlink(missing_ok=True)
            if idx < len(versions) - 1 and _should_retry(getattr(e, "output", None)):
                continue
            raise
        inp.unlink(missing_ok=True)
        if build_mode == "apk":
            final = Path(f"{app_name}-{arch}-morphe-v{version}.apk")
            apksigner = utils.find_apksigner()
            if apksigner:
                utils.run_process([apksigner, "sign", "--ks", "keystore/unified.jks", "--ks-pass", "pass:morphe",
                                   "--key-pass", "pass:morphe", "--ks-key-alias", "morphe",
                                   "--in", str(out), "--out", str(final)])
                out.unlink(missing_ok=True)
            else:
                out.rename(final)
            print(f"BUILT {final}")
            return str(final)
        else:
            # module path handled by module_builder
            from src import module_builder

            z = module_builder.build_module(out, app_name, source, arch, version, app_cfg, pkg or "")
            print(f"BUILT {z}")
            return str(z)
    return None


def main():
    data = utils.load_unified()
    only_app = (getenv("APP_NAME") or "").strip()
    only_source = (getenv("SOURCE") or "").strip()
    only_arch = (getenv("ARCH") or "").strip()
    only_mode = (getenv("MODE") or getenv("BUILD_MODE") or "").strip()
    built = []
    for app in data["apps"]:
        if only_app and app["app_name"] != only_app:
            continue
        if only_source and app["source"] != only_source:
            continue
        for arch in app.get("arches", ["universal"]):
            if only_arch and arch != only_arch:
                continue
            for mode in app.get("build_modes", ["apk"]):
                if only_mode and mode != only_mode:
                    continue
                logging.info(f"building {app['app_name']} {arch} {mode}")
                try:
                    r = run_build(app["app_name"], app["source"], arch, mode, app)
                    if r:
                        built.append(r)
                except Exception as e:
                    logging.error(f"build failed {app['app_name']} {arch} {mode}: {e}")
    print(f"BUILT {len(built)} outputs")
    for b in built:
        print(f" - {b}")


if __name__ == "__main__":
    main()
