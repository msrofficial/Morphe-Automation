# Morphe-Automation

Unified Morphe builder — patched APK + Magisk modules with fully automated daily builds.

![Repo Views](https://komarev.com/ghpvc/?username=msrofficial&repo=Morphe-Automation&label=Repo+Views&color=blue&style=flat)
[![Build](https://github.com/msrofficial/Morphe-Automation/actions/workflows/build.yml/badge.svg)](https://github.com/msrofficial/Morphe-Automation/actions/workflows/build.yml)
[![License](https://img.shields.io/github/license/msrofficial/Morphe-Automation)](LICENSE)
[![Release](https://img.shields.io/github/v/release/msrofficial/Morphe-Automation?include_prereleases)](https://github.com/msrofficial/Morphe-Automation/releases)
[![Telegram](https://img.shields.io/badge/Telegram-Morphe_Builds-blue?logo=telegram)](https://t.me/morpheautomation)

<p align="center">
  <a href="https://t.me/morpheautomation">
    <img src="https://img.shields.io/badge/Join_Telegram_Channel-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" height="60" alt="Join Telegram Channel" />
  </a>
</p>

Currently builds YouTube, YouTube Music and Reddit in `universal` arch, each as APK and Magisk module. Configuration is data-driven; no code change is needed to add versions, arches, or modes.

## Contents

- Features
- Telegram
- Quick start
- Configuration overview
- How it works
- Workflows overview
- Requirements
- Docs
- License

## Features

- Patched APK (with MicroG support) + Magisk modules (root, no MicroG needed)
- Auto daily builds via GitHub Actions (schedule + manual trigger)
- Multi-source stock fetcher with fallback: Archive to APKMirror to Uptodown / APKPure / Direct
- Auto patch planning (MicroG / branding handling for APK vs module)
- Auto APK signing + signature guard + integrity check
- Bundle merge via APKEditor for split APKs
- Smart release cleanup — keep newest 3 releases, prune old files only (releases kept)
- Telegram release notification with download links (HTML, BD time)
- Manifest history carried on update branch

## Telegram

Build updates: [Morphe Automation Builds](https://t.me/morpheautomation)

Release notifications include APK links, MicroG note with download link, module links, date in Asia/Dhaka time, and channel footer links.

## Quick start

1. Edit `unified.json` — enable apps, set `arches` and `build_modes` (`apk`, `module`).
2. Run manual workflow (`Actions -> Manual Build`) or locally:

```bash
pip install -r requirements.txt
mkdir -p build temp build_records
python -m src
```

Filtered local run:

```bash
APP_NAME=youtube SOURCE=morphe ARCH=universal MODE=apk python -m src
```

Termux:

```bash
./build-termux.sh
```

3. Get outputs from Releases:
   - `youtube-universal-morphe-v*.apk`
   - `youtube-music-universal-morphe-v*.apk`
   - `reddit-universal-morphe-v*.apk`
   - `youtube-morphe-module-v*-universal.zip`
   - `music-morphe-module-v*-universal.zip`
   - `reddit-morphe-module-v*-universal.zip`
   - `manifest.json`

## Configuration overview

- `unified.json` — apps, arches, modes, version policy, module metadata. See [CONFIGURATION](docs/CONFIGURATION.md).
- `sources/morphe.json` — Morphe CLI + patches GitHub releases.
- `apps/archive/*.json`, `apps/apkmirror/*.json` — stock package, dlurl/org, arch, pinned version.
- `patches/*.txt` — `+include` / `-exclude` rules. Empty (comment only) means defaults + auto MicroG/branding.
- `sig.txt` — optional signature whitelist.
- `keystore/unified.jks` — APK signing key, auto-generated in CI if missing.

Example target matrix from default config: 3 apps x 1 arch x 2 modes = 6 targets.

## How it works

```
unified.json -> targets -> download CLI/patches -> download stock (fallback chain)
  -> signature guard -> patch rules -> retry over versions
  -> bundle merge -> arch strip -> integrity check
  -> patch -> sign (apk) / pack module (zip)
  -> record + manifest + release + telegram + cleanup
```

Details: [ARCHITECTURE](docs/ARCHITECTURE.md)

## Workflows overview

- `build.yml` (scheduled daily 06:00 UTC + manual dispatch with force rebuild):
  check/audit -> matrix build-apps -> release + manifest + telegram + cleanup.
- `manual.yml` (manual single app/source/arch/mode, including both):
  build only, upload artifact, no release.

Details: [WORKFLOWS](docs/WORKFLOWS.md)

## Requirements

- Python 3.11 with `requirements.txt` (`requests`, `beautifulsoup4`, `PyGithub`)
- Java 21 (Temurin in CI)
- `zip`, `unzip`
- `GITHUB_TOKEN` for GitHub API (CI provides automatically)
- Optional for notify: `TG_TOKEN`, `TG_CHAT`, channel link envs

## Docs

- [INSTALLATION](docs/INSTALLATION.md) — APK + MicroG + module install guide for end users
- [CONFIGURATION](docs/CONFIGURATION.md) — unified.json, sources, apps, patches, signing, env vars
- [WORKFLOWS](docs/WORKFLOWS.md) — local build, scheduled/manual CI, audit/record/manifest/prune, telegram format, retention
- [ARCHITECTURE](docs/ARCHITECTURE.md) — pipeline, modules, invariants, known gaps
- [FAQ](docs/FAQ.md) — troubleshooting and how to add a new app

## License

See [LICENSE](LICENSE) and [NOTICE](NOTICE).
