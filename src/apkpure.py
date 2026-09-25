"""APKPure + Uptodown + Archive + Direct simplified fetchers."""
from src.session import session


def _apkpure_latest(pkg):
    # APKPure version API via website search is unstable; return None to let
    # caller fall back to CLI-supported versions list.
    return None


def get_latest_version(app_name, cfg):
    return None


def get_download_link(version, app_name, cfg):
    return None
