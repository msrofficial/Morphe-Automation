# Morphe-Automation

Unified Morphe builder — patched APK + Magisk modules with fully automated daily builds.

![Repo Views](https://komarev.com/ghpvc/?username=msrofficial&repo=Morphe-Automation&label=Repo+Views&color=blue&style=flat)
[![Build](https://github.com/msrofficial/Morphe-Automation/actions/workflows/build.yml/badge.svg)](https://github.com/msrofficial/Morphe-Automation/actions/workflows/build.yml)
[![License](https://img.shields.io/github/license/msrofficial/Morphe-Automation)](LICENSE)
[![Release](https://img.shields.io/github/v/release/msrofficial/Morphe-Automation?include_prereleases)](https://github.com/msrofficial/Morphe-Automation/releases)
[![Telegram](https://img.shields.io/badge/Telegram-Morphe_Builds-blue?logo=telegram)](https://t.me/morpheautomation)

## Features

- Patched APK (with MicroG support) + Magisk modules (root, no MicroG needed)
- Auto daily builds via GitHub Actions (schedule + manual trigger)
- Multi-source stock fetcher with fallback: Archive to APKMirror to Uptodown / APKPure / Direct
- Auto patch planning (MicroG / branding handling for APK vs module)
- Auto APK signing + signature guard + integrity check
- Smart release cleanup — keep newest 3 releases, prune old files only (releases kept)
- Telegram release notification with download links (HTML)
- manifest.json history carried on update branch

## Telegram

Build updates: https://t.me/morpheautomation

## Quick start

1. Edit `unified.json` — enable apps, set `build_modes` (`apk`, `module`)
2. Run manual workflow (`Actions -> Manual Build`) or locally:
   ```bash
   ./build.sh
   # or filtered:
   APP_NAME=youtube SOURCE=morphe ARCH=universal MODE=apk ./build.sh
   ```
3. Get outputs from Releases: `*-morphe-*.apk` + `*-module-*.zip` + `manifest.json`

See `unified.json` for full schema and `docs/ARCHITECTURE.md` for design.

## Configuration

`unified.json` example:

```json
{
  "apps": [
    {
      "app_name": "youtube",
      "source": "morphe",
      "arches": ["universal"],
      "build_modes": ["apk", "module"],
      "version": "auto",
      "dpi": "nodpi",
      "include_stock": "merged",
      "module_prop_name": "youtube-morphe"
    }
  ]
}
```

- `apps/*.json` — per-source stock config (package, dlurl, org)
- `sources/*.json` — Morphe CLI / patches GitHub releases
- `patches/*.txt` — `+include` / `-exclude` patch rules (`# default` = use defaults)

## How it works

```
unified.json -> targets -> download stock -> merge bundle -> strip libs
  -> patch (morphe-cli) -> sign (apk) / pack module (zip)
  -> release + manifest + telegram notify + cleanup
```

- Entry: `python -m src` (`src/__main__.py`, `src/cli.py`, `src/models.py`)
- Fetch: `src/fetcher.py` + `src/adapters/*` + `src/downloader.py` + `src/apkmirror.py`, `archive.py`, etc.
- Patch: `src/patch_v2.py` / `src/patcher.py` + `src/utils.py` (versions, signing, integrity)
- Package: `src/packager.py` / `src/module_builder.py` + `module/*.sh` (on-device installer)
- Tools: `tools/tool.py` (`audit|note|join|prune`) + `scripts/*` shims

## Workflows

- `build.yml` — daily `06:00 UTC`: check updates to matrix build to release to manifest to `update` branch to Telegram to cleanup (`--keep-n 3`)
- `manual.yml` — on-demand single `app/source/arch/mode` build

## Requirements

- Python 3.11 (`requirements.txt`: `requests`, `beautifulsoup4`, `PyGithub`)
- Java 21, `zip/unzip`, `keystore/unified.jks` (auto-generated in CI if missing)

## License

See [LICENSE](LICENSE) and [NOTICE](NOTICE).
