# FAQ and Troubleshooting

## Builds fail with download failed

- Check `apps/archive/<app>.json` `dlurl` is reachable. Archive listing must contain `<version>-<arch>.apk` style names.
- APKMirror HTML selectors change often. If `apkmirror_adapter` and legacy `apkmirror.py` both fail, pin `version` in `apps/*/<app>.json` or `unified.json` to a known-good stock.
- `updown` / `apkpure` always fail by design (stubs). Do not rely on them in source order.

## list-versions returns empty

- `utils.get_supported_versions` runs `java -jar <cli> list-versions`. Requires Java 21 and matching CLI/patches pair from the same release.
- If output starts with `usage:` / `unmatched argument` / `error`, it returns `[]` and caller falls back to adapter `latest()` only.
- Test locally: `java -jar morphe-cli-*.jar list-versions -f com.google.android.youtube --patches morphe-patches-*.mpp`.

## Patch aborts with fingerprint mismatch

- Normal. `__main__._should_retry` detects `failed to match the fingerprint`, `PatchException`, `patching aborted` and retries with the next candidate version automatically.
- If all versions fail, update Morphe CLI + patches (`sources/morphe.json` tag `latest`) or pin an older stock version.

## APK does not install

- `INSTALL_FAILED_UPDATE_INCOMPATIBLE` / downgrade: uninstall old variant, then install new. Signatures must match across updates from the same keystore.
- `check_apk_integrity` failed: re-download, check disk space, ensure APKEditor merge succeeded for bundles.

## Module aborts with version mismatch

- Installer compares installed stock `versionName` with module `PKG_VER`. If no `stock/base.apk` is bundled, it aborts.
- Fix: set `include_stock` to `merged` (default) or flash the matching stock version first.

## Wrong arch

- `customize.sh` aborts if `MODULE_ARCH` (from build arch) differs from device `ARCH`. Rebuild with `ARCH=universal` or the correct `arm64-v8a` / `armeabi-v7a`.

## Telegram notify skipped

- Workflow skips if `TG_TOKEN` or `TG_CHAT` is empty. Set repo Secrets and make the bot a channel admin with Post Messages permission.
- Test format locally by printing `MSG` with `parse_mode=HTML` in a private chat before using the channel.

## Manifest is empty or missing entries

- `build_records/*.json` are created per built file. `join` merges them with `new_manifest.json` (previous `update` branch) into `manifest.json`.
- If artifacts failed to upload, `release` job has no records to merge. Check `build-apps` logs for `BUILD FAILED: no final outputs`.

## Old releases still take space

- `prune_old_releases --keep-n 3` deletes files but keeps release shells. Increase `--keep-n` to keep more, or manually `gh release delete <tag>` to remove a whole release.
- Same-tag reruns only prune same-prefix old files via `prune_release`.

## How do I add a new app?

1. Add `apps/archive/<newapp>.json` and `apps/apkmirror/<newapp>.json` with `package`, `dlurl`/`org`, `name`.
2. Add entry in `unified.json` with `arches` and `build_modes`.
3. Add `patches/<newapp>-morphe.txt` (can be a single comment line for defaults).
4. Add `sig.txt` line if signature enforcement is needed.
5. Run `MODE=apk` manual build first, then enable `module`.
