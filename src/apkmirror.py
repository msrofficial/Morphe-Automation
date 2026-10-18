"""APKMirror fetcher via HTML parsing."""
import random
import re
import time
from bs4 import BeautifulSoup
from src.session import session


def _page(url, retries=3):
    last = None
    for i in range(retries):
        try:
            time.sleep(2 + random.random() * 3)
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last = e
            # 429 -> back off longer
            time.sleep(5 * (i + 1) + random.random() * 5)
            continue
    raise last


def get_latest_version(app_name, cfg):
    org = cfg.get("org", "")
    name = cfg.get("name", app_name)
    html = _page(f"https://www.apkmirror.com/uploads/?appcategory={name}")
    m = re.findall(r"Version:</span><span class=\"infoSlide-value\">(.*?) </span>", html)
    vers = [v.strip() for v in m if "beta" not in v.lower() and "alpha" not in v.lower()]
    return vers[0] if vers else None


def _slug(version: str) -> str:
    from src.utils import base_version

    return base_version(version).replace(" ", "-").replace(".", "-")


def _row_text(a) -> str:
    try:
        row = a.find_parent("div", class_="table-row")
        return row.get_text(" ", strip=True).lower() if row else ""
    except Exception:
        return ""


def get_download_link(version, app_name, cfg):
    org = cfg.get("org", "")
    name = cfg.get("name", app_name)
    # version pages may use a longer slug than the app directory (e.g. gboard
    # dir is /gboard/ but pages are /gboard-the-google-keyboard-<ver>-release/)
    page_slug = cfg.get("app_slug") or name
    arch = str(cfg.get("arch", "universal")).lower()
    dpi = str(cfg.get("dpi", "nodpi")).lower()
    page = _page(f"https://www.apkmirror.com/apk/{org}/{name}/{page_slug}-{_slug(version)}-release/")
    soup = BeautifulSoup(page, "html.parser")

    def _abs(href):
        if not href:
            return ""
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("http"):
            return href if "apkmirror.com" in href else ""
        return "https://www.apkmirror.com" + href

    links = []
    seen = set()
    for a in soup.select("div.table-row a"):
        href = a.get("href", "")
        # variant rows link to .../<variant>-android-apk-download/ (skip #comments dup)
        if href.startswith("/apk/") and "-android-apk-download/" in href and href not in seen:
            seen.add(href)
            links.append((href, _row_text(a)))
    # own preference: nodpi/requested arch first, plain release APK over beta/lite/bundle
    def score(item):
        _, text = item
        s = 0
        if "nodpi" in text or dpi in text:
            s += 2
        if arch and arch in text:
            s += 3
        elif "universal" in text or "all" in text:
            s += 2
        elif arch in ("universal", "all", "") and "arm64-v8a" in text:
            s += 1
        if "bundle" in text or "apkm" in text:
            s -= 1
        if "beta" in text:
            s -= 2
        if "lite" in text:
            s -= 3
        return s
    links.sort(key=score, reverse=True)
    for href, _ in links:
        try:
            dl_page = _page(_abs(href))
        except Exception:
            continue
        s2 = BeautifulSoup(dl_page, "html.parser")
        btn = s2.select_one("a.btn")
        if btn and btn.get("href"):
            try:
                dl2 = _page(_abs(btn["href"]))
            except Exception:
                continue
            s3 = BeautifulSoup(dl2, "html.parser")
            fin = s3.select_one("span > a[rel=nofollow]") or s3.select_one("a[rel=nofollow]")
            if fin and fin.get("href"):
                return _abs(fin["href"])
    return None
