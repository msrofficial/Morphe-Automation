# Installation

This guide covers end-user installation. For build setup, see WORKFLOWS.md.

## 1. APK (non-root)

Applies to: `youtube-universal-morphe-v*.apk`, `youtube-music-universal-morphe-v*.apk`

Steps:

1. Uninstall existing YouTube / YT Music updates if signature mismatch occurs (backup data if needed).
2. Install MicroG RE first (required for Google login):
   - Download: [MicroG RE](https://morphe.software/microg)
   - Install normally, open once, grant required permissions, enable device spoofing if asked.
3. Install the Morphe APK from GitHub Releases or Telegram channel:
   - [GitHub Releases](https://github.com/msrofficial/Morphe-Automation/releases)
   - [Telegram Channel](https://t.me/morpheautomation)
4. Open the app, login with Google via MicroG, disable battery optimization for MicroG + YouTube if login drops.

Notes:

- APKs are signed with `keystore/unified.jks` in CI. After first install, keep updating from the same source to avoid signature mismatch.
- If `INSTALL_FAILED_UPDATE_INCOMPATIBLE` appears, uninstall the old variant fully, then reinstall.
- `universal` APKs have `lib/x86` and `lib/x86_64` stripped to reduce size. They work on arm64 and arm devices.

## 2. Magisk module (root)

Applies to: `youtube-morphe-module-v*-universal.zip`, `music-morphe-module-v*-universal.zip`

Requirements:

- Magisk / KernelSU / APatch
- Stock YouTube / YT Music installed (same version as `PKG_VER` in module, or bundled `stock/base.apk` will be used to update)

Steps:

1. Download the module zip from Releases or Telegram.
2. Flash via Magisk app (Modules -> Install from storage) or KernelSU equivalent.
3. Follow on-screen installer output in `module/customize.sh`:
   - Wrong-arch check (`MODULE_ARCH` vs device `ARCH`)
   - Stock version check (must match `PKG_VER` unless stock APK is bundled)
   - Stock APK install via `pmex install-create/write/commit`
   - Native lib extraction to app lib dir
   - Bind-mount of patched `base.apk` to `/data/adb/rvhc/*.apk`
4. Do not reboot unless installer asks (system-app downgrade case creates a `post-fs-data.d` script and asks for reboot + reflash).
5. After install, force-stop happens automatically and `cmd package compile -m speed-profile` optimizes the app.

On-device files:

- `module/config` — `PKG_NAME`, `PKG_VER`, `MODULE_ARCH`
- `module/module.prop` + `module.prop.orig` — Magisk metadata + `updateJson`
- `module/utils.sh`, `customize.sh`, `service.sh`, `action.sh`, `uninstall.sh` — mount / enable / disable / cleanup logic
- `service.sh` remounts on boot after `sys.boot_completed=1`
- `action.sh` toggles mount via Magisk action button (creates/removes `disabled_by_action`)

Disable / remove:

- Use Magisk action button to disable (unmounts, keeps files), press again to re-enable.
- Remove module fully via Magisk Manager, then reboot if mounts persist (`umount_all` in `utils.sh`).

## 3. MicroG FAQ (YouTube / YT Music only, Reddit needs no MicroG)

- Login fails / spins: reinstall MicroG RE, clear data of MicroG + YouTube, re-login.
- Battery optimization kills MicroG: set MicroG + patched apps to Unrestricted.
- Two MicroGs installed: keep only [MicroG RE](https://morphe.software/microg).

## 4. Version matching

Module `config` example:

```
PKG_NAME=com.google.android.youtube
PKG_VER=20.10.35
MODULE_ARCH=
```

If installed stock version differs from `PKG_VER` and no `stock/base.apk` is bundled (`include_stock=disable`), install aborts with version mismatch. Use the APK release or wait for a module built for your stock version.
