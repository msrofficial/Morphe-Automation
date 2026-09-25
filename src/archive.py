"""Archive.org fetcher: dlurl is a directory listing with files like pkg-version-arch.apk."""
import re
from src.session import session


def get_latest_version(app_name, cfg):
    dlurl = (cfg.get("dlurl") or "").rstrip("/")
    if not dlurl:
        return None
    r = session.get(dlurl, timeout=30)
    r.raise_for_status()
    files = re.findall(r'href="([^"]+\.(?:apk|apkm))"', r.text)
    vers = []
    for f in files:
        m = re.search(r"-(\d[\d.\s]*)-(all|arm64-v8a|arm-v7a)\.", f)
        if m:
            vers.append(m.group(1).strip())
    from src.utils import get_highest_version

    return get_highest_version(vers)


def get_download_link(version, app_name, cfg):
    from src import downloader as _d  # noqa

    dlurl = (cfg.get("dlurl") or "").rstrip("/")
    v = version.replace(" ", "")
    arch = (cfg.get("arch") or "all").replace(" ", "")
    r = session.get(dlurl, timeout=30)
    r.raise_for_status()
    files = re.findall(r'href="([^"]+\.(?:apk|apkm))"', r.text)
    for f in files:
        if f"{v}-{arch}" in f:
            return f"{dlurl}/{f}"
    for f in files:
        if f"{v}-all" in f:
            return f"{dlurl}/{f}"
    return None
