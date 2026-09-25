# Morphe-Automation

Unified Morphe builder — APK + Magisk modules, auto daily builds.

Merged from:
- `j-hc/revanced-magisk-module` (module power, bash `build_rv`, mount logic)
- `RookieEnough/morphe-AutoBuilds` (Python factory, 100+ apps, multi-source)

## Quick start
1. Edit `unified.json` — enable apps, set `build_modes`
2. Run manual workflow or `./build.sh`
3. Get outputs from Releases (`*.apk` + `*-module.zip`) + `manifest.json` + `*-update.json`

See `unified.json` for schema.
