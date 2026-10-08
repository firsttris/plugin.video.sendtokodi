---
description: How to install the SendToKodi add-on in Kodi 19, 20 and 21 on Windows, Linux, macOS, Android, LibreELEC and CoreELEC, with automatic updates from the SendToKodi repository.
---

# Installation

SendToKodi is not in the official Kodi add-on repository, so you install it from the **SendToKodi repository**. The
repository is itself a tiny add-on; once it is installed, Kodi finds SendToKodi in *Install from repository* and keeps
it up to date automatically.

## Requirements

- **Kodi 19 (Matrix) or newer**: Kodi 19, 20 (Nexus) and 21 (Omega) are supported. Older releases use Python 2 and
  cannot run the add-on.
- **A platform yt-dlp runs on**: Windows, Linux, macOS, Android, LibreELEC and CoreELEC all work. On Android, Kodi's
  bundled Python runs yt-dlp as well.
- **Internet access from the Kodi device**: the add-on downloads yt-dlp and, for YouTube, the Deno JavaScript runtime
  on first use (see [First start](#first-start)).
- **Dependencies** (installed automatically by Kodi): `script.module.inputstreamhelper` for the adaptive streaming
  checks and `script.module.requests`.

!!! note "InputStream Adaptive"
    Adaptive streams (DASH and HLS, used by YouTube and most large sites) play through Kodi's
    [InputStream Adaptive](https://kodi.wiki/view/Add-on:InputStream_Adaptive) add-on. It comes with Kodi on
    Windows, macOS, Android, LibreELEC and CoreELEC; some Linux distributions package it separately
    (`kodi-inputstream-adaptive`). *Settings → Adaptive → Check if my Kodi supports adaptive streaming* confirms it
    is available and enables it when needed.

## Install from the SendToKodi repository (recommended)

1. Download the repository ZIP to a place your Kodi device can reach (a USB stick, a network share or the device
   itself): [repository.sendtokodi-1.0.0.zip](https://github.com/firsttris/repository.sendtokodi/raw/refs/heads/master/repository.sendtokodi-1.0.0.zip)
2. In Kodi, allow installation from unknown sources once: *Settings → System → Add-ons → Unknown sources*.
3. Go to *Add-ons → Install from zip file*, pick the downloaded ZIP and confirm. Kodi reports *SendToKodi
   Repository add-on installed*.
4. Go to *Add-ons → Install from repository → SendToKodi Repository → Video add-ons → SendToKodi* and choose
   *Install*. Kodi installs the dependencies with it.

From now on Kodi updates SendToKodi together with its other add-ons. If you turned off automatic add-on updates, new
versions appear under *Add-ons → My add-ons → Video add-ons → SendToKodi → Update*.

Reference: [Add-on manager in the Kodi wiki](https://kodi.wiki/view/Add-on_manager).

## Install a release ZIP by hand

Every [GitHub release](https://github.com/firsttris/plugin.video.sendtokodi/releases/latest) also carries the add-on
as `plugin.video.sendtokodi-<version>.zip`. Install it with *Add-ons → Install from zip file*. Kodi installs the
dependencies from its own repository. Without the SendToKodi repository you have to install future versions the same
way, so the repository above is the better choice for everyday use.

## First start

The add-on keeps its own copy of yt-dlp and, when needed, of the Deno JavaScript runtime, in its data folder. On the
first playback, or when you open the settings for the first time:

- **yt-dlp** is downloaded from the latest [yt-dlp release](https://github.com/yt-dlp/yt-dlp/releases). If
  *Auto-update yt-dlp* is off, the add-on asks once whether to download it.
- **Deno** is downloaded from the [Deno releases](https://github.com/denoland/deno/releases) when the JavaScript
  runtime mode is *auto* or *deno*. YouTube requires a JavaScript runtime since 2025, so leave this enabled unless
  your platform cannot run Deno (see [ARMv7 devices](troubleshooting.md#armv7-devices-raspberry-pi-2-and-3-32-bit)).

Both downloads happen once; afterwards the add-on checks for updates every six hours in the background. You can see
the installed versions and trigger updates in the [settings](settings.md).

## The companion apps

The add-on receives links; something else has to send them. Install at least one of these, all described in
[Usage](usage.md):

| Device | App | Install |
|---|---|---|
| Chrome, Edge, Brave, Vivaldi, Opera | SendToKodi browser extension | [Chrome Web Store](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf), [Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/sendtokodi/cfaaejdnkempodfadjkjfblimmakeaij) |
| Firefox | SendToKodi browser extension | [Mozilla Add-ons](https://addons.mozilla.org/firefox/addon/sendtokodi/) |
| Android | Kore, the official Kodi remote | [Google Play](https://play.google.com/store/apps/details?id=org.xbmc.kore) |
| iPhone, iPad, Mac | Apple Shortcut | [SendToKodi-OSX.shortcut](https://raw.githubusercontent.com/firsttris/plugin.video.sendtokodi/refs/heads/master/SendToKodi-OSX.shortcut) |

The browser extension and the Shortcut talk to Kodi over its web server, so turn on *Allow remote control via HTTP*
in *Settings → Services → Control* and set a username and password. Kore uses the same setting.

## Updating

With the SendToKodi repository installed, Kodi updates the add-on on its own. Updates of **yt-dlp** and **Deno** are
independent of add-on updates: the add-on fetches them itself (see [Settings](settings.md#yt-dlp)). A website that
stopped playing is usually fixed by a new yt-dlp version, not by a new add-on version, so check
*Settings → yt-dlp → Update yt-dlp now* first.

## Uninstalling

*Add-ons → My add-ons → Video add-ons → SendToKodi → Uninstall*. Kodi asks whether to delete the add-on's settings
and data as well; answering *Yes* also removes the downloaded yt-dlp and Deno versions, the downloaded media and the
subtitle cache. The folders are listed in [How it works](how-it-works.md#files-on-disk) if you want to remove them by
hand.
