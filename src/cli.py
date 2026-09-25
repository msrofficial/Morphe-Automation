"""New CLI entry (v2). Legacy shim: delegates to src.__main__ until Phase 2-3 land."""
import logging
import os
from pathlib import Path

from src import utils
from src.models import targets_from_unified

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    data = utils.load_unified()
    targets = targets_from_unified(
        data,
        only_app=(os.environ.get("APP_NAME") or "").strip(),
        only_source=(os.environ.get("SOURCE") or "").strip(),
        only_arch=(os.environ.get("ARCH") or "").strip(),
        only_mode=(os.environ.get("MODE") or os.environ.get("BUILD_MODE") or "").strip(),
    )
    logging.info(f"v2 cli: {len(targets)} targets")
    # Phase 1: delegate each target to legacy run_build to keep CI green
    from src.__main__ import run_build

    built = []
    for t in targets:
        logging.info(f"building {t.app.app_name} {t.arch} {t.mode}")
        try:
            r = run_build(t.app.app_name, t.app.source, t.arch, t.mode, t.app.__dict__)
            if r:
                built.append(r)
        except Exception as e:
            logging.error(f"failed {t.key}: {e}")
    print(f"BUILT {len(built)} outputs")
    for b in built:
        print(f" - {b}")


if __name__ == "__main__":
    main()
