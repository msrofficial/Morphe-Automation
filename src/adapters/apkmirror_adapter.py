"""APKMirror adapter (fallback). Own selectors + polite delay."""
import re
from bs4 import BeautifulSoup
from src.fetcher import SourceAdapter, _get, register


@register
class ApkmirrorAdapter(SourceAdapter):
    name = "apkmirror"

    def latest(self, app_name, cfg):
        name = cfg.get("name", app_name)
        html = _get(f"https://www.apkmirror.com/uploads/?appcategory={name}").text
        m = re.findall(r"Version:</span><span class=\"infoSlide-value\">(.*?) </span>", html)
        vers = [v.strip() for v in m if "beta" not in v.lower() and "alpha" not in v.lower()]
        return vers[0] if vers else None

    def link(self, version, app_name, cfg):
        from src.utils import base_version

        org = cfg.get("org", "")
        name = cfg.get("name", app_name)
        page_slug = cfg.get("app_slug") or name
        arch = str(cfg.get("arch", "universal")).lower()
        dpi = str(cfg.get("dpi", "nodpi")).lower()
        slug = base_version(version).replace(" ", "-").replace(".", "-")
        page = _get(f"https://www.apkmirror.com/apk/{org}/{name}/{page_slug}-{slug}-release/").text
        soup = BeautifulSoup(page, "html.parser")

        def row_text(a):
            row = a.find_parent("div", class_="table-row")
            return row.get_text(" ", strip=True).lower() if row else ""

        def score(a):
            text = row_text(a)
            s = 0
            if "nodpi" in text or dpi in text:
                s += 2
            if "universal" in text or "all" in text or arch in text:
                s += 2
            elif arch in ("universal", "all", "") and "arm64-v8a" in text:
                s += 1
            if "bundle" in text or "apkm" in text:
                s -= 1
            return s

        cands = []
        seen = set()
        for a in soup.select("div.table-row a"):
            href = a.get("href", "")
            if "/apk/" in href and "download" not in href and href not in seen:
                seen.add(href)
                cands.append(a)
        cands.sort(key=score, reverse=True)
        for a in cands:
            p2 = _get("https://www.apkmirror.com" + a["href"]).text
            btn = BeautifulSoup(p2, "html.parser").select_one("a.btn")
            if btn and btn.get("href"):
                p3 = _get("https://www.apkmirror.com" + btn["href"]).text
                fin = BeautifulSoup(p3, "html.parser").select_one("a[rel=nofollow]")
                if fin and fin.get("href"):
                    return "https://www.apkmirror.com" + fin["href"]
        return None
