"""Direct URL fetcher: dlurl points to a file; version/arch validated by name."""


def get_latest_version(app_name, cfg):
    dlurl = cfg.get("dlurl", "")
    name = dlurl.rstrip("/").split("/")[-1]
    parts = name.split("-")
    if len(parts) >= 3:
        return parts[1]
    return None


def get_download_link(version, app_name, cfg):
    dlurl = cfg.get("dlurl", "")
    v = version.replace(" ", "")
    arch = (cfg.get("arch") or "all").replace(" ", "")
    if f"{v}-{arch}" not in dlurl and f"{v}-all" not in dlurl:
        return None
    return dlurl
