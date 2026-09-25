"""Archive.org adapter (primary reliable source). Own implementation."""
import re
from src.fetcher import SourceAdapter, _get, register


@register
class ArchiveAdapter(SourceAdapter):
    name = "archive"

    def latest(self, app_name, cfg):
        from src.utils import get_highest_version

        dlurl = (cfg.get("dlurl") or "").rstrip("/")
        if not dlurl:
            return None
        html = _get(dlurl).text
        files = re.findall(r'href="([^"]+\.(?:apk|apkm))"', html)
        vers = []
        for f in files:
            m = re.search(r"-(\d[\d.\s]*)-(all|arm64-v8a|arm-v7a|universal)\.", f)
            if m:
                vers.append(m.group(1).strip())
        return get_highest_version(vers)

    def link(self, version, app_name, cfg):
        dlurl = (cfg.get("dlurl") or "").rstrip("/")
        v = version.replace(" ", "")
        arch = (cfg.get("arch") or "all").replace(" ", "")
        # universal accepts any variant, prefer fullest first
        if arch in ("universal", "all", ""):
            wanted = ["arm64-v8a", "arm-v7a", "all", "universal"]
        else:
            wanted = [arch, "all"]
        html = _get(dlurl).text
        files = re.findall(r'href="([^"]+\.(?:apk|apkm))"', html)
        for w in wanted:
            for f in files:
                if f"{v}-{w}" in f:
                    return f"{dlurl}/{f}"
        return None
