"""Download morphe tools + stock APKs from all sources."""
import json
import logging
import time
from pathlib import Path

from src import utils
from src.session import session


def download_resource(url: str, name: str = None) -> Path:
    res = session.get(url, stream=True, timeout=60)
    res.raise_for_status()
    final_url = res.url
    if not name:
        cd = res.headers.get("content-disposition", "")
        if "filename=" in cd:
            name = cd.split("filename=")[-1].strip().strip('"')
        else:
            name = Path(final_url.split("?")[0]).name or "download.bin"
    fp = Path(name)
    total = int(res.headers.get("content-length", 0))
    done = 0
    with fp.open("wb") as f:
        for chunk in res.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                done += len(chunk)
    logging.info(f"download {final_url} [{done}/{total}] -> {fp}")
    return fp


def github_release(user: str, repo: str, tag: str = "latest"):
    token = __import__("os").environ.get("GITHUB_TOKEN") or __import__("os").environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    base = f"https://api.github.com/repos/{user}/{repo}/releases"
    if tag == "latest":
        r = session.get(base + "/latest", headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    if tag in ("", "dev", "prerelease"):
        r = session.get(base, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            raise ValueError(f"no releases for {user}/{repo}")
        return data[0]
    r = session.get(f"{base}/tags/{tag}", headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def download_required(source: str):
    sp = Path("sources") / f"{source}.json"
    with sp.open() as f:
        info = json.load(f)
    name = info[0].get("name", source)
    files = []
    for entry in info[1:]:
        rel = github_release(entry["user"], entry["repo"], entry.get("tag", "latest"))
        ename = entry.get("repo", "").lower()
        for asset in rel.get("assets", []):
            aname = asset.get("name", "")
            url = asset.get("browser_download_url")
            if not url or aname.endswith(".asc") or aname.endswith(".json"):
                continue
            if "morphe-patches" in ename or "morphe-cli" in ename:
                if aname.endswith(".mpp") or aname.endswith(".jar"):
                    files.append(download_resource(url))
            else:
                files.append(download_resource(url))
    return files, name


def _load_app_config(app_name: str, platform: str):
    p = Path("apps") / platform / f"{app_name}.json"
    if p.exists():
        with p.open() as f:
            return json.load(f)
    # synthesize from another platform if package known
    for other in ["apkmirror", "uptodown", "apkpure", "archive", "direct"]:
        if other == platform:
            continue
        q = Path("apps") / other / f"{app_name}.json"
        if q.exists():
            try:
                with q.open() as f:
                    o = json.load(f)
                if o.get("package"):
                    return {
                        "name": o.get("name", app_name),
                        "package": o["package"],
                        "version": o.get("version", ""),
                        "arch": o.get("arch", "universal"),
                        "type": o.get("type", "APK"),
                        "dpi": o.get("dpi", "nodpi"),
                        "org": o.get("org", app_name),
                        "dlurl": o.get("dlurl", ""),
                    }
            except Exception:
                continue
    return None


def download_platform(app_name, platform, cli, patches, arch=None, override_version=None):
    cfg = _load_app_config(app_name, platform)
    if not cfg or not cfg.get("package"):
        raise FileNotFoundError(f"no config for {app_name} on {platform}")
    if arch and arch != "universal":
        cfg["arch"] = arch
    elif not cfg.get("arch"):
        cfg["arch"] = arch or "universal"
    mod = __import__(f"src.{platform}", fromlist=["x"])
    pinned = (cfg.get("version") or "").strip()
    if override_version:
        candidates = [override_version]
    elif pinned:
        candidates = [pinned]
    else:
        candidates = utils.get_supported_versions(cfg["package"], cli, patches)
        try:
            latest = mod.get_latest_version(app_name, cfg)
            if latest and latest not in candidates:
                candidates.append(latest)
        except Exception as e:
            logging.debug(f"latest lookup failed: {e}")
    last_err = None
    for ver in candidates:
        if not ver:
            continue
        link = mod.get_download_link(ver, app_name, cfg)
        if not link:
            last_err = ValueError(f"no link for {app_name} {ver}")
            continue
        try:
            fp = download_resource(link)
            return fp, ver, candidates
        except Exception as e:
            last_err = e
            continue
    raise last_err or ValueError(f"no downloadable version for {app_name}")


def _wrap(platform):
    def fn(app_name, cli, patches, arch=None, override_version=None):
        try:
            return download_platform(app_name, platform, cli, patches, arch, override_version)
        except Exception as e:
            logging.error(f"{platform} failed: {e}")
            return None, None, []

    fn.__name__ = f"download_{platform}"
    return fn


download_apkmirror = _wrap("apkmirror")
download_apkpure = _wrap("apkpure")
download_uptodown = _wrap("uptodown")
download_archive = _wrap("archive")
download_direct = _wrap("direct")


def download_apkeditor() -> Path:
    for _ in range(3):
        try:
            rel = github_release("REAndroid", "APKEditor", "latest")
            for a in rel.get("assets", []):
                if a["name"].startswith("APKEditor") and a["name"].endswith(".jar"):
                    return download_resource(a["browser_download_url"])
            raise RuntimeError("APKEditor jar not found")
        except Exception as e:
            logging.warning(f"apkeditor retry: {e}")
            time.sleep(2)
    raise RuntimeError("APKEditor download failed")
