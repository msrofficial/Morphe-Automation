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
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://apkpure.com/",
}


def _load(url: str, retries: int = 3):
    last = None
    for i in range(retries):
        try:
            time.sleep(1.5 + random.random() * 2.0)
            r = session.get(url, headers=_HEADERS, timeout=25)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def get_latest_version(app_name, cfg):
    name = (cfg.get("name") or app_name or "").strip()
    pkg = (cfg.get("package") or "").strip()
    if not name or not pkg:
        return None
    url = f"https://apkpure.com/{name}/{pkg}/versions"
    try:
        r = _load(url)
    except Exception as e:
        logging.debug(f"apkpure latest miss {app_name}: {e}")
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


def get_download_link(version, app_name, cfg):
    name = (cfg.get("name") or app_name or "").strip()
    pkg = (cfg.get("package") or "").strip()
    if not version or not name or not pkg:
        return None
    url = f"https://apkpure.com/{name}/{pkg}/download/{str(version).strip()}"
    try:
        r = _load(url)
    except Exception as e:
        logging.debug(f"apkpure link miss {app_name} {version}: {e}")
        return None
    try:
        soup = BeautifulSoup(r.content, "html.parser")
        a = soup.find("a", id="download_link")
        if a and a.get("href"):
            href = a["href"].strip()
            if href.startswith("/"):
                return "https://apkpure.com" + href
            return href
        fast = soup.select_one("a[href*='download'][href$='.apk']")
        if fast and fast.get("href"):
            return fast["href"]
    except Exception as e:
        logging.debug(f"apkpure link parse miss {app_name}: {e}")
    return None
