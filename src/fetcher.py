"""v2 stock fetcher: adapter registry + cache + backoff (Phase 2)."""
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path

from src.session import session

CACHE_DIR = Path.home() / ".cache" / "morphe"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class FetchResult:
    path: Path
    version: str
    candidates: list


class SourceAdapter:
    name = "base"

    def latest(self, app_name, cfg):
        raise NotImplementedError

    def link(self, version, app_name, cfg):
        raise NotImplementedError


def _get(url, retries=4):
    last = None
    for i in range(retries):
        try:
            time.sleep(1.5 + random.random() * 2.5)
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(4 * (i + 1) + random.random() * 4)
    raise last


def download_url(url: str, dest: Path) -> Path:
    res = _get(url)
    name = dest.name
    cd = res.headers.get("content-disposition", "")
    if "filename=" in cd and dest.name.startswith("tmp"):
        name = cd.split("filename=")[-1].strip().strip('"')
        dest = dest.parent / name
    total = int(res.headers.get("content-length", 0))
    done = 0
    with dest.open("wb") as f:
        for chunk in res.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                done += len(chunk)
    logging.info(f"fetched {url} [{done}/{total}] -> {dest}")
    return dest


REGISTRY: dict = {}


def register(adapter: SourceAdapter):
    REGISTRY[adapter.name] = adapter
    return adapter


def get_adapter(name: str) -> SourceAdapter:
    return REGISTRY[name]
