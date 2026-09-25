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


def get_download_link(version, app_name, cfg):
    # Simplified: search uploads page then first variant page.
    # Full dpi/arch filtering happens after download attempt; caller retries.
    org = cfg.get("org", "")
    name = cfg.get("name", app_name)
    ver_slug = version.replace(" ", "-").replace(".", "-")
    page = _page(f"https://www.apkmirror.com/apk/{org}/{name}/{name}-{ver_slug}-release/")
    soup = BeautifulSoup(page, "html.parser")
    # find first APK/BUNDLE row link
    for a in soup.select("div.table-row a"):
        href = a.get("href", "")
        if "/apk/" in href and "download" not in href:
            dl_page = _page("https://www.apkmirror.com" + href)
            s2 = BeautifulSoup(dl_page, "html.parser")
            btn = s2.select_one("a.btn")
            if btn and btn.get("href"):
                dl2 = _page("https://www.apkmirror.com" + btn["href"])
                s3 = BeautifulSoup(dl2, "html.parser")
                fin = s3.select_one("span > a[rel=nofollow]")
                if fin and fin.get("href"):
                    return "https://www.apkmirror.com" + fin["href"]
    return None
