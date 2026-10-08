---
description: Reference for every SendToKodi setting in Kodi: auto-download, JavaScript runtime (Deno, QuickJS), yt-dlp release channel and updates, yt-dlp config file, adaptive streaming, DASH builder, stream selection and maximum resolution.
---

# Settings

Open the settings in Kodi via *Add-ons → My add-ons → Video add-ons → SendToKodi → Configure*, or by opening the
add-on from *Add-ons → Video add-ons*. Some settings are only visible at Kodi's *Advanced* or *Expert* settings level
(the button at the bottom left of the dialog); the tables say which.

## General

| Setting | Default | What it does |
|---|---|---|
| **Auto-download resolved media before playback** | off | Downloads the media file to disk first and plays the local file afterwards. For unstable connections, expiring streams or keeping a copy. A playlist is downloaded video by video as it plays. See [Downloading instead of streaming](usage.md#downloading-instead-of-streaming). |
| **Media download path** (Advanced) | `special://profile/addon_data/plugin.video.sendtokodi/downloads` | Folder for the downloaded files. Any Kodi path works, including network shares. Only shown when auto-download is on. |
| **Enable legacy Python embed workarounds** (Expert) | off | Compatibility patch for a `stderr` quirk of Kodi's embedded Python on some old builds. Keep it off unless a traceback in the log mentions `isatty`. |

## JavaScript Runtime

YouTube and a few other sites protect their streams with JavaScript challenges. yt-dlp solves them with an external
JavaScript runtime; without one, YouTube playback fails. The add-on manages [Deno](https://deno.com) for this and can
use [QuickJS](https://bellard.org/quickjs/) as a lighter alternative.

| Setting | Default | What it does |
|---|---|---|
| **JavaScript runtime mode** | `auto` | `auto`: Deno where available, QuickJS on ARMv7 devices when a QuickJS path is set. `deno`: always Deno. `quickjs`: always the QuickJS binary from the path below. `disabled`: no JavaScript runtime; YouTube will not play. |
| **QuickJS binary path** (Advanced) | empty | Path to a `qjs` executable. Only shown in `quickjs` mode. Needed on ARMv7 devices (Raspberry Pi 2 and 3 with a 32-bit OS), for which Deno has no build. See [ARMv7 devices](troubleshooting.md#armv7-devices-raspberry-pi-2-and-3-32-bit). |
| **Auto-update Deno JavaScript runtime** | on | Downloads Deno when missing and checks for new releases every six hours. |
| **Installed Deno version** | | Read-only display of the installed version. |
| **Manage Deno version** | | Opens a list of the latest 20 Deno releases plus the versions already installed. Choose one to install or activate it; installed versions can be deleted from the same list. Up to three installed versions are kept. |
| **Update Deno now** | | Checks for the latest release and installs it immediately. |

## yt-dlp

[yt-dlp](https://github.com/yt-dlp/yt-dlp) does the actual resolving. It changes often, because websites change often,
so the add-on keeps its own copy and updates it independently of add-on releases.

| Setting | Default | What it does |
|---|---|---|
| **yt-dlp release channel** | `Stable` | `Stable` uses the official yt-dlp releases. `Nightly` uses the [nightly builds](https://github.com/yt-dlp/yt-dlp-nightly-builds) of yt-dlp's master branch, which often contain site fixes (for YouTube in particular) weeks before the next stable release. `System` uses a yt-dlp that is already importable by Kodi's Python, for example a distribution package, and downloads nothing. A channel switch takes effect with the next download; until then **Installed yt-dlp version** keeps showing the version in use. |
| **Auto-update yt-dlp** | on | Downloads yt-dlp when missing and checks for new releases of the chosen channel every six hours. When off, the add-on asks once per day whether to download a missing yt-dlp. |
| **Installed yt-dlp version** | | Read-only display of the version in use. For the `System` channel this is the version Kodi's Python imports. |
| **Manage yt-dlp version** | | Opens a list of the latest 20 releases of the chosen channel plus the installed versions. Choose one to install or activate it; installed versions can be deleted. Up to three installed versions are kept, so you can go back to an older one when a new release breaks a site. |
| **Update yt-dlp now** | | Checks for the latest release of the chosen channel and installs it immediately. |
| **yt-dlp config file** | empty | Optional path to a [yt-dlp configuration file](https://github.com/yt-dlp/yt-dlp#configuration), in yt-dlp's own format: one command line option per line, for example `--cookies`, `--extractor-args` or `--socket-timeout`. Only the options set in this file are applied; yt-dlp's default config locations are not read. Files on network sources (`smb://`, `nfs://`) are copied locally before loading. See [Using a yt-dlp config file](#using-a-yt-dlp-config-file). |

!!! tip "System channel"
    With `System`, the package **and its dependencies** must be importable by Kodi's Python, otherwise the add-on
    reports that yt-dlp is unavailable. This mode is meant for platforms that package yt-dlp themselves; on a normal
    Kodi installation, stay on `Stable` or `Nightly`.

### Using a yt-dlp config file

Anything you would pass to yt-dlp on the command line can go into the config file. Common uses:

```text
# Log in to sites that require it, with cookies exported from your browser
--cookies /storage/.kodi/userdata/addon_data/plugin.video.sendtokodi/cookies.txt

# Prefer a different YouTube client
--extractor-args "youtube:player_client=tv"

# Tolerate slow sites
--socket-timeout 30

# Use a proxy
--proxy socks5://127.0.0.1:1080
```

Cookies are the usual answer to *Sign in to confirm you're not a bot*, age-restricted and members-only videos; the
[yt-dlp wiki](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) explains how to export them.
Options that control downloading (output templates, post-processors) only matter when auto-download is on. The file is
re-read on every playback, so changes apply immediately. An invalid option shows *Could not load yt-dlp config* and the
details are in Kodi's log.

## Adaptive

Settings for adaptive streaming through [InputStream Adaptive](https://kodi.wiki/view/Add-on:InputStream_Adaptive)
(ISA), which handles DASH and HLS streams with quality switching.

| Setting | Default | What it does |
|---|---|---|
| **Check if my Kodi supports adaptive streaming** | | Runs the InputStream Helper check, which shows whether ISA is installed and enabled and installs it if possible. |
| **Use original manifest (experimental)** | on | Hands the site's own DASH or HLS manifest to ISA when yt-dlp reports one. When off, the add-on prefers direct stream URLs or its own DASH manifest. |
| **Use DASH manifest builder (kodi 19+ only) (experimental)** | on | Builds a DASH manifest from the separate video and audio streams a site offers (YouTube serves its high resolutions only this way) and serves it to ISA from a local HTTP server. When off, only formats that already contain video and audio together play, which on YouTube means 720p at most. See [The DASH manifest builder](how-it-works.md#the-dash-manifest-builder). |
| **DASH MPD server idle timeout (seconds)** | 120 | After this many seconds without a request, the next request for the generated manifest regenerates it with fresh stream URLs. 10 to 600 seconds. Only shown when the DASH builder is on. |
| **Ask which stream to play** | off | Shows a list of all formats yt-dlp found before every playback and plays the one you choose. See [Stream selection](usage.md#stream-selection). |
| **Audio-only HLS: disable Opus for native m3u streams** | on | Skips Opus audio in audio-only HLS streams that Kodi plays natively (without ISA), which Kodi's HLS demuxer cannot handle. Turn off only if an audio stream has no other codec. |
| **Maximum resolution** | 1920x1080 (FHD) | Caps the width of the video stream the add-on selects or puts into its DASH manifest: 8K, 4K, 2K, Full HD, HD or SD. *Adaptive (auto quality)* removes the cap and leaves the choice to ISA, which adapts to the bandwidth. |
