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
        org = cfg.get("org", "")
        name = cfg.get("name", app_name)
        slug = version.replace(" ", "-").replace(".", "-")
        page = _get(f"https://www.apkmirror.com/apk/{org}/{name}/{name}-{slug}-release/").text
        soup = BeautifulSoup(page, "html.parser")
        for a in soup.select("div.table-row.headerFont a"):
            href = a.get("href", "")
            if "/apk/" in href and "download" not in href:
                p2 = _get("https://www.apkmirror.com" + href).text
                btn = BeautifulSoup(p2, "html.parser").select_one("a.btn")
                if btn and btn.get("href"):
                    p3 = _get("https://www.apkmirror.com" + btn["href"]).text
                    fin = BeautifulSoup(p3, "html.parser").select_one("a[rel=nofollow]")
                    if fin and fin.get("href"):
                        return "https://www.apkmirror.com" + fin["href"]
        return None
