# Architecture

Independent 4-layer design. Legacy `src/*` flat files are kept as shims until v2 paths prove green; new code must not import legacy downloader internals.

```
src/
  models.py        BuildTarget, AppSpec, BuildResult (dataclasses, no logic)
  cli.py           v2 entry, delegates to __main__.run_build per target
  __main__.py      orchestrator: unified.json -> download -> patch -> apk/module
  utils.py         run_process, versions, files, signing, integrity, signatures
  session.py       shared requests.Session with browser UA
  fetcher.py       v2 registry (SourceAdapter, register, get_adapter, download_url)
  downloader.py    legacy download_required, github_release, download_platform, apkeditor
  apkmirror.py     legacy HTML fetcher
  apkpure.py       own APKPure listing + download-page fetcher
  uptodown.py      own store-page + versions-API fetcher
  archive.py       legacy archive.org fetcher
  direct.py        direct URL fetcher
  patcher.py       legacy rule engine + microg/branding detect + build_command
  patch_v2.py      v2 rule engine (PatchRequest, read_rules, find_special_patches)
  packager.py      v2 module writer (package_module)
  module_builder.py legacy module writer (build_module)
  adapters/
    archive_adapter.py    primary reliable source
    apkmirror_adapter.py  fallback source
tools/
  tool.py          audit|note|join|prune (own implementation)
scripts/
  check_updates.py  shim -> tool.audit
  record_build.py   shim -> tool.note
  merge_manifest.py shim -> tool.join
  cleanup_old.py    shim -> tool.prune_release + prune_old_releases
module/
  customize.sh, utils.sh, service.sh, action.sh, uninstall.sh
  on-device installer, mount, boot remount, toggle, uninstall
```

## Pipeline details

`run_build(app_name, source, arch, build_mode, app_cfg)`:

1. `download_required(source)` loads `sources/<source>.json`, calls GitHub API (`github_release`) with `GITHUB_TOKEN` if present, downloads CLI `.jar` and patches `.mpp`/`.jar`. Locates files via `utils.find_file(suffix=.jar, contains=morphe-cli)` and `.mpp`.
2. Stock loop order `archive, apkmirror, uptodown, apkpure, direct`. For `archive`/`apkmirror`, v2 adapter path runs first if `apps/<platform>/<app>.json` has `package`: builds `tries` from `get_supported_versions(package, cli, patches)` (CLI `list-versions`) plus adapter `latest()`, then `link()` + `download_url()` per version. On exception, falls back to legacy `download_<platform>(app, cli, patches, arch)`. First success wins.
3. Signature guard: loads `package` from first existing `apps/*/<app>.json`, runs `check_sig(bin/apksigner.jar, apk, package)` against `sig.txt`. Mismatch only warns.
4. Patch rules: `patch_v2.read_rules` (fallback `patcher.read_patch_rules`) plus `find_special_patches` / `detect_microg_branding` via `java -jar <cli> list-patches --with-packages`. MicroG included (`-e`) for APK, excluded (`-d`) for module; branding excluded for module.
5. Retry list `versions = [version] + [others]`. On `CalledProcessError` with fingerprint/patch-aborted output (`_should_retry`), deletes outputs and retries with next version (re-download via `override_version`).
6. Bundle merge: non-`.apk` zips containing `.apk` entries are merged with `REAndroid/APKEditor` (`java -jar ... m -f -i <in> -o <merged>`).
7. Arch strip: APK mode strips `lib/x86/*, lib/x86_64/*` always, plus opposite ARM ABI if arch is pinned. Module mode strips all `lib/*` later in packager (stock provides libs).
8. Integrity: `check_apk_integrity` (zipfile test). Patch cmd: `java -jar <cli> patch --patches <patches> --out <out> <in> + inc/exc + patcher_args`.
9. Finalize APK: `apksigner sign --ks keystore/unified.jks` to `<app>-<arch>-morphe-v<version>.apk`, else rename.
10. Finalize module: `packager.package_module` (fallback `module_builder.build_module`): copy `module/` template to `temp/`, write `config` and `module.prop` (with `NEXT_VER_CODE` and `updateJson`), strip `lib/*` from patched APK to `base.apk`, optionally copy latest stock to `stock/base.apk`, zip with `compresslevel`.

## Key invariants

- New code uses domain names (`fetch_stock`, `apply_patches`, `package_module`). Legacy stays as fallback until manual green run.
- Every phase keeps CI green: v2 first, legacy fallback on exception.
- No network scraping without backoff: `_page` / `_get` sleep 1.5-5s plus 4-5s per retry, 3-4 retries.
- `load_unified` dedups `(app_name, source)`.
- `normalize_version` handles `X.Y.Z`, `build N`, `(code)` suffixes for highest-version comparison.

## Known gaps

- All stock sources use own implementations; no vendored scraper code is used.
- `ARCHITECTURE.md` previously described `core/fetch,patch,package` paths that do not exist; actual code is flat under `src/`. This file supersedes that sketch.
- Duplicate logic exists intentionally (patcher/patch_v2, packager/module_builder, apkmirror/adapter) for safe migration. Do not delete legacy until v2 is default in CI.
