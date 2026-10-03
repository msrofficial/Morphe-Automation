# Configuration

All build behavior is driven by `unified.json` plus per-app JSON files. No code change is needed for normal use.

## 1. unified.json

Location: repo root `unified.json`. Deduplicated by `(app_name, source)` on load (`src/utils.py:load_unified`).

Full example:

```json
{
  "defaults": {
    "patches-source": "morphe",
    "cli-source": "morphe",
    "compression-level": 9,
    "remove-integrations-checks": true
  },
  "apps": [
    {
      "app_name": "youtube",
      "source": "morphe",
      "arches": ["universal"],
      "build_modes": ["apk", "module"],
      "version": "auto",
      "dpi": "nodpi",
      "include_stock": "merged",
      "enable_update_checks": false,
      "module_prop_name": "youtube-morphe",
      "patcher_args": ""
    },
    {
      "app_name": "youtube-music",
      "source": "morphe",
      "arches": ["universal"],
      "build_modes": ["apk", "module"],
      "version": "auto",
      "dpi": "nodpi",
      "include_stock": "merged",
      "enable_update_checks": false,
      "module_prop_name": "music-morphe",
      "patcher_args": ""
    }
  ]
}
```

Field reference:

- `app_name`: must match `apps/<platform>/<app_name>.json` and `patches/<app_name>-<source>.txt`
- `source`: key of `sources/<source>.json` (currently only `morphe`)
- `arches`: list, e.g. `["universal"]` or `["arm64-v8a", "armeabi-v7a", "universal"]`. Each arch becomes a separate matrix target.
- `build_modes`: subset of `["apk", "module"]`. Each mode becomes a separate target.
- `version`: `auto` (use CLI-supported + latest) or pinned like `"20.10.35"`. Pinned skips version lookup.
- `dpi`: passed through to app config, currently `nodpi`.
- `include_stock`: `merged` (bundle `stock/base.apk` into module) or `disable` (patched APK only).
- `enable_update_checks`: reserved, currently unused by patcher.
- `module_prop_name`: Magisk `id` in `module.prop`. Falls back to `<app_name>-morphe`.
- `patcher_args`: extra raw args appended to `java -jar <cli> patch ...`.

Env filters (CI matrix and local):

- `APP_NAME`, `SOURCE`, `ARCH`, `MODE` (or `BUILD_MODE`). Empty means all. `MODE=both` is handled only in `manual.yml` by running apk then module sequentially.

## 2. sources/*.json

Example `sources/morphe.json`:

```json
[
  { "name": "morphe" },
  { "user": "MorpheApp", "repo": "morphe-cli", "tag": "latest" },
  { "user": "MorpheApp", "repo": "morphe-patches", "tag": "latest" }
]
```

- Entry 0: logical name.
- Entry 1..n: GitHub releases to download. `tag` can be `latest`, `dev`/`prerelease` (first release), or a fixed tag.
- `src/downloader.py:download_required` downloads `.jar` / `.mpp` assets (skips `.asc`, `.json`). CLI is detected by filename containing `morphe-cli`, patches by `.mpp` or `patches` + `.jar`.

## 3. apps/*/*.json

Per-platform stock source config. Search order in `run_build` is `archive, apkmirror, uptodown, apkpure, direct`.

Archive example (`apps/archive/youtube.json`):

```json
{
  "name": "youtube",
  "package": "com.google.android.youtube",
  "version": "",
  "arch": "universal",
  "type": "APK",
  "dpi": "nodpi",
  "org": "youtube",
  "dlurl": "https://archive.org/download/jhc-apks/apks/com.google.android.youtube"
}
```

APKMirror example (`apps/apkmirror/youtube.json`):

```json
{
  "org": "google-inc",
  "name": "youtube",
  "type": "APK",
  "arch": "universal",
  "dpi": "nodpi",
  "package": "com.google.android.youtube",
  "version": ""
}
```

- `package`: Android package name, used for `list-versions` and signature check.
- `version`: pinned version override. Empty means auto.
- `arch`: `universal` accepts `arm64-v8a, arm-v7a, all, universal` (preferred in that order).
- `dlurl`: archive directory listing or direct file URL.
- Missing platform file is synthesized from another platform if `package` is known (`_load_app_config`).

Current status: `apkpure` and `uptodown` fetchers are stubs returning `None` (`src/apkpure.py`, `src/uptodown.py`). Effective sources are `archive` (primary) and `apkmirror` (fallback).

## 4. patches/*.txt

File: `patches/<app_name>-<source>.txt`, e.g. `patches/youtube-morphe.txt`.

Syntax (one per line):

```
# comment / empty = use defaults
+Patch Name To Include
-Patch Name To Exclude
```

Parsed by `src/patch_v2.py:read_rules` (v2) and `src/patcher.py:read_patch_rules` (legacy) into `-e` / `-d` CLI flags. Current shipped files contain only a comment, meaning defaults plus auto MicroG/branding rules:

- MicroG/GmsCore patch detected via `list-patches --with-packages`: APK mode adds `-e <microg>`, module mode adds `-d <microg>`.
- Custom branding patch: module mode adds `-d <branding>`.

## 5. Signing and keys

- `sig.txt`: whitelist lines `<sha256> <package>`. If package is listed, `utils.check_sig` verifies with `bin/apksigner.jar` or system `apksigner`. Archive re-signed stock only warns and continues.
- `keystore/unified.jks`: APK signing key (alias `morphe`, storepass `morphe`). CI generates it if missing. Never commit a production keystore to a public fork without rotation.
- `compression-level`: 0-9 for module zip (`packager.py` / `module_builder.py`). Defaults to 9.

## 6. Environment variables

- Build filters: `APP_NAME`, `SOURCE`, `ARCH`, `MODE`
- GitHub: `GITHUB_TOKEN` / `GH_TOKEN`, `GITHUB_REPOSITORY` (for `updateJson` URL), `NEXT_VER_CODE` (Magisk `versionCode`, defaults to date)
- Telegram notify (release job): `TG_TOKEN`, `TG_CHAT`, optional `INDEX_LINK`, `BUILDS_LINK`, `PATCH_LINK`, `DISCUSS_LINK`, `BACKUP_LINK`
- Audit: `FORCE_FULL_REBUILD=true` forces full matrix
- Record: `APK_PATH` override for `scripts/record_build.py`
