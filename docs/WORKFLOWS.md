# Workflows and Builds

## 1. Local build

Requirements: Python 3.11, Java 21, `zip/unzip`.

```bash
pip install -r requirements.txt
mkdir -p build temp build_records
python -m src
```

Filtered:

```bash
APP_NAME=youtube SOURCE=morphe ARCH=universal MODE=apk python -m src
MODE=module python -m src
```

Wrapper script `build.sh` does the same. Termux quick start is in `build-termux.sh` (installs `git python openjdk-21 zip unzip`, clones repo, installs requirements, runs `build.sh`).

Outputs:

- Patched intermediate: `<app>-<arch>-patch-v<version>.apk` (deleted after sign/pack on success)
- Final APK: `<app>-<arch>-morphe-v<version>.apk` in repo root
- Final module: `build/<app>-morphe-module-v<version>-<arch>.zip`
- Records: `build_records/<stem>.json` via `scripts/record_build.py` (or `tools/tool.py note`)
- Manifest: `manifest.json` via `scripts/merge_manifest.py` (or `tools/tool.py join`)

Failure rule in CI: if no `*-morphe-*.apk` and no `build/*` outputs exist after build, the job exits 1.

## 2. Scheduled workflow (.github/workflows/build.yml)

Trigger: daily cron `0 6 * * *` plus `workflow_dispatch` with `force_full_rebuild` boolean.

Jobs:

1. `check` (audit):
   - `pip install -r requirements.txt`
   - `python scripts/check_updates.py` (shim for `tools/tool.py audit`)
   - Compares each target key `<app>|<source>|<arch>|<mode>` in `manifest.json` (from `update` branch history) against current Morphe patches tag from GitHub API.
   - If `FORCE_FULL_REBUILD=true`, full matrix is emitted.
   - Outputs: `has_updates`, `build_matrix`, `update_count`, `total_count`, `carry_count` to `GITHUB_OUTPUT` and `build_matrix.json`.
2. `build-apps` (matrix, only if `has_updates == true`):
   - Setup Python 3.11, Java 21 (temurin), `zip/unzip`.
   - Ensure keystore exists or generate with `keytool`.
   - Env: `APP_NAME/SOURCE/ARCH/MODE` from matrix, `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `NEXT_VER_CODE=run_number`.
   - Run `python -m src`, remove stock leftovers (`com.*.apk`), record each `*-morphe-*.apk` / `build/*` via `record_build.py`.
   - Upload artifact `out-<app>-<source>-<arch>-<mode>` with APKs, zips, `build_records/`. Fails if no files.
3. `release`:
   - Download all `out-*` artifacts to `./all`, copy `*-morphe-*.apk` / `*-module-*.zip` to `release-apks/`, drop `com.*` leftovers.
   - Fetch previous `manifest.json` from `update` branch as merge base (`new_manifest.json`), then `merge_manifest.py`.
   - `keep.txt` is built from current `release-apks` basenames.
   - Publish: `TAG=v<run_number>`. If tag exists, `gh release upload --clobber`, else `gh release create --latest=false`.
   - Cleanup: `python scripts/cleanup_old.py --release $TAG --keep-file keep.txt --keep-n 3`.
   - Push `manifest.json` to `update` branch (orphan if missing).
   - Telegram notify (HTML links, BD time `Asia/Dhaka` as `UTC+6`, APK section + MicroG note + module section + channel footer). Skipped if `TG_TOKEN` / `TG_CHAT` are empty.

## 3. Manual workflow (.github/workflows/manual.yml)

Trigger: `workflow_dispatch` with inputs `app_name` (default `youtube`), `source` (default `morphe`), `arch` (`arm64-v8a|armeabi-v7a|universal`), `mode` (`apk|module|both`).

- `mode=both` runs `MODE=apk python -m src` then `MODE=module python -m src`, else single `python -m src`.
- Uploads `*-morphe-*.apk`, `build/*.apk`, `build/*.zip` as `manual-<app>-<arch>-<mode>`. No release, no manifest, no Telegram.

## 4. Audit, record, manifest, prune

All in `tools/tool.py`, with shims in `scripts/` for old workflow paths:

- `audit [--force]`: see section 2 step 1. Used by `scripts/check_updates.py`.
- `note`: parses `APK_PATH` (or newest `*-morphe-*.apk` / `build/*.zip`) with regex `(.+)-([^-]+)-morphe(?:-module)?-v(.+).(\w+)` plus env `APP_NAME/SOURCE/ARCH/MODE`, writes `build_records/<stem>.json`. Used by `scripts/record_build.py`.
- `join`: merges `new_manifest.json` (if present) + all `build_records/*.json` into `manifest.json` keyed by `<app>|<source>|<arch>|<mode>`. Used by `scripts/merge_manifest.py`.
- `prune --release --keep-file --keep-n 3 [--skip-old]`:
  - `prune_release`: within the given release, deletes assets sharing the same prefix `(.+-[^-]+-morphe)(?:-module)?-v` that are not in `keep.txt`.
  - `prune_old_releases`: lists up to 200 releases sorted by `createdAt` desc, keeps newest N, deletes all asset files from older releases but keeps the release shells. Used by `scripts/cleanup_old.py`.

## 5. Telegram notification format

Current template in `build.yml` (HTML `parse_mode`, `disable_web_page_preview=true`):

- Title: `Morphe-Automation $TAG published`
- Date: `TZ=Asia/Dhaka date +%d %B %Y %I:%M %p (UTC+6)` (12-hour + AM/PM, BD time)
- APK section: loop `release-apks/*.apk` with `<a href=release-download-url>name</a>`
- MicroG note + `Click Here` to `https://morphe.software/microg`
- Module section: loop `release-apks/*.zip`
- Footer: `Need all files and tutorials in one place? Join MSR IndeX` plus `Builds | PatcH | Discussion | Backup` links (defaults overridable via `INDEX_LINK` etc. env).

Required secrets: `TG_TOKEN` (bot token), `TG_CHAT` (channel `@morpheautomation` or `-100...` ID). Bot must be channel admin with Post Messages permission.

## 6. Release retention policy

- Each run creates a new tag `v<run_number>` (`--latest=false`, so GitHub Latest stays manual).
- `keep.txt` protects current run files in the current tag.
- `prune_old_releases --keep-n 3` keeps the newest 3 releases fully intact. Older releases keep their title/notes but lose their files. Change retention by editing `--keep-n` in `build.yml`.
- To keep more history, increase `--keep-n` or set `--latest=true` handling separately.
