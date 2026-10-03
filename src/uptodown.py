"""Uptodown fetcher (own implementation).

Resolves the public store page for an app slug, reads the versions list,
then follows the version page to the direct download button.
"""
import logging
import random
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.session import session

_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch(url: str, retries: int = 3):
    last = None
    for i in range(retries):
        try:
            time.sleep(1.5 + random.random() * 2.0)
            r = session.get(url, headers=_UA, timeout=25)
            if r.status_code == 200 and r.content:
                return r
            last = ValueError(f"status {r.status_code}")
        except Exception as e:
            last = e
        time.sleep(3 * (i + 1))
    if last:
        raise last
    return None


def _slugs(cfg: dict) -> list:
    out = []
    raw = str(cfg.get("slug") or cfg.get("name") or "").strip().lower()
    pkg = str(cfg.get("package") or "").strip().lower()

    def add(v: str):
        v = (v or "").strip().lower()
        if v and len(v) > 1 and v not in out:
            out.append(v)

    add(raw)
    add(raw.replace("-", ""))
    add(raw.replace("-", "_"))
    if pkg:
        tail = pkg.split(".")[-1]
        add(tail)
        add(pkg.replace(".", "-"))
    for suffix in ("-android", "-mobile", "-app"):
        add(raw + suffix)
    return out[:8]


def _detail_ok(resp) -> bool:
    try:
        soup = BeautifulSoup(resp.content, "html.parser")
        return soup.find("h1", id="detail-app-name") is not None
    except Exception:
        return False


def get_latest_version(app_name, cfg):
    for slug in _slugs(cfg):
        url = f"https://{slug}.en.uptodown.com/android/versions"
        try:
            r = _fetch(url)
        except Exception as e:
            logging.debug(f"uptodown slug miss {slug}: {e}")
            continue
        if not r:
            continue
        try:
            soup = BeautifulSoup(r.content, "html.parser")
            items = [n.get_text(strip=True) for n in soup.select("#versions-items-list .version")]
            items = [v for v in items if v]
            if items:
                return items[0]
            single = soup.select_one("div.version, [itemprop='softwareVersion']")
            if single and single.get_text(strip=True):
                return single.get_text(strip=True)
        except Exception as e:
            logging.debug(f"uptodown parse miss {slug}: {e}")
            continue
    return None


def get_download_link(version, app_name, cfg):
    if not version:
        return None
    want = re.sub(r"\s+", " ", str(version)).strip()
    for slug in _slugs(cfg):
        base = f"https://{slug}.en.uptodown.com/android"
        try:
            listing = _fetch(base + "/versions")
        except Exception:
            continue
        if not listing or not _detail_ok(listing):
            continue
        try:
            soup = BeautifulSoup(listing.content, "html.parser")
            code_node = soup.find("h1", id="detail-app-name")
            code = code_node.get("data-code") if code_node else None
            if not code:
                continue
            # scan first pages of version API for exact version row
            for page in range(1, 4):
                api = f"{base}/apps/{code}/versions/{page}"
                try:
                    r = _fetch(api)
                    entries = (r.json() or {}).get("data") or []
                except Exception:
                    break
                if not entries:
                    break
                hit = None
                for e in entries:
                    if str(e.get("version", "")).strip() == want:
                        hit = e
                        break
                if not hit:
                    continue
                parts = hit.get("versionURL") or {}
                vurl = "/".join(str(parts.get(k, "")).strip("/") for k in ("url", "extraURL", "versionID"))
                if not vurl.startswith("http"):
                    continue
                try:
                    vpage = _fetch(vurl)
                except Exception:
                    continue
                vsoup = BeautifulSoup(vpage.content, "html.parser")
                btn = vsoup.find(id="detail-download-button")
                if btn:
                    nxt = btn.get("data-url") or btn.get("href") or ""
                    if nxt and nxt != "apps":
                        if nxt.startswith("http") or "dw.uptodown.com" in nxt or nxt.endswith((".apk", ".xapk")):
                            return urljoin("https://dw.uptodown.com/dwn/", nxt) if not nxt.startswith("http") else nxt
                link = vsoup.select_one("a.download[href]")
                if link and link.get("href"):
                    return urljoin(vpage.url, link["href"])
                continue
        except Exception as e:
            logging.debug(f"uptodown link miss {slug}: {e}")
            continue
    return None
