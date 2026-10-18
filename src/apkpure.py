"""APKPure fetcher (own implementation).

Uses the public version listing and per-version download page.
"""
import logging
import random
import time

from bs4 import BeautifulSoup

from src.session import session

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://apkpure.com/",
    "Upgrade-Insecure-Requests": "1",
}

_warmed = False


def _warm():
    """Prime cookies/clearance on the site root before deep pages."""
    global _warmed
    if _warmed:
        return
    _warmed = True
    try:
        session.get("https://apkpure.com/", headers=_HEADERS, timeout=20)
    except Exception as e:
        logging.info(f"apkpure warm-up failed: {e}")


def _load(url: str, retries: int = 2):
    last = None
    for i in range(retries):
        try:
            time.sleep(1.0 + random.random() * 1.5)
            r = session.get(url, headers=_HEADERS, timeout=25)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def get_latest_version(app_name, cfg):
    name = (cfg.get("name") or app_name or "").strip()
    pkg = (cfg.get("package") or "").strip()
    if not name or not pkg:
        return None
    _warm()
    url = f"https://apkpure.com/{name}/{pkg}/versions"
    try:
        r = _load(url)
    except Exception as e:
        logging.info(f"apkpure latest miss {app_name}: {e}")
        return None
    try:
        soup = BeautifulSoup(r.content, "html.parser")
        top = soup.find("div", class_="ver-top-down")
        if top and top.get("data-dt-version"):
            return top["data-dt-version"].strip()
        # fallback: first version row
        row = soup.select_one(".ver-item .ver-n, .version-list .version")
        if row and row.get_text(strip=True):
            return row.get_text(strip=True).split()[0]
    except Exception as e:
        logging.debug(f"apkpure parse miss {app_name}: {e}")
    return None


def _version_forms(version, cfg):
    """APKPure keys downloads by the full store version (e.g.
    18.0.3.954559732-release-arm64-v8a); also try the stripped base."""
    from src.utils import base_version

    raw = str(version or "").strip()
    base = base_version(raw)
    arch = str(cfg.get("arch") or "").strip().lower()
    archs = ["arm64-v8a", "armeabi-v7a"] if arch in ("", "universal", "all") else [arch]
    forms = []
    for v in (raw, base):
        if not v:
            continue
        for cand in [v] + [f"{v}-release-{a}" for a in archs]:
            if cand not in forms:
                forms.append(cand)
    return forms


def get_download_link(version, app_name, cfg):
    name = (cfg.get("name") or app_name or "").strip()
    pkg = (cfg.get("package") or "").strip()
    if not version or not name or not pkg:
        return None
    _warm()
    for form in _version_forms(version, cfg):
        url = f"https://apkpure.com/{name}/{pkg}/download/{form}"
        try:
            r = _load(url)
        except Exception as e:
            logging.info(f"apkpure link miss {app_name} {form}: {e}")
            continue
        try:
            soup = BeautifulSoup(r.content, "html.parser")
            a = soup.find("a", id="download_link")
            if a and a.get("href"):
                href = a["href"].strip()
                if href.startswith("/"):
                    href = "https://apkpure.com" + href
                logging.info(f"apkpure link ok {app_name} {form} -> {href[:120]}")
                return href
            fast = soup.select_one("a[href*='download'][href$='.apk']")
            if fast and fast.get("href"):
                logging.info(f"apkpure fallback link ok {app_name} {form}")
                return fast["href"]
            logging.info(
                f"apkpure page ok but no link {app_name} {form} "
                f"(status {r.status_code}, len {len(r.content)}, title "
                f"{soup.title.get_text(strip=True) if soup.title else '?'!r})"
            )
        except Exception as e:
            logging.info(f"apkpure link parse miss {app_name}: {e}")
    return None
