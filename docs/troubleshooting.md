---
description: Fix SendToKodi problems in Kodi. Video doesn't play, "Could not resolve the url", YouTube "Sign in to confirm you're not a bot", yt-dlp unavailable, Deno on Raspberry Pi and ARMv7, adaptive streaming, where to find the Kodi log and how to report a bug.
---

# Troubleshooting

Most problems have one of three causes: the website changed and yt-dlp needs an update, the JavaScript runtime is
missing, or the client cannot reach Kodi. This page goes from the most common to the rare ones.

## First steps for any problem

1. **Update yt-dlp.** *Settings → yt-dlp → Update yt-dlp now*. Websites change constantly and the fix is almost
   always a new yt-dlp. If the stable release doesn't help, switch the **yt-dlp release channel** to *Nightly*, which
   gets site fixes weeks earlier, and update again.
2. **Check the URL with yt-dlp outside Kodi.** On any computer with yt-dlp installed:

    ```bash
    yt-dlp --simulate "<url>"   # can yt-dlp resolve it at all?
    yt-dlp -g "<url>"           # the direct media URLs yt-dlp would pick
    ```

    If yt-dlp fails there too, the problem is in yt-dlp or the website, not in the add-on. Search
    [yt-dlp's issues](https://github.com/yt-dlp/yt-dlp/issues) for the site; once yt-dlp fixes it, the add-on picks
    up the fix with its next update check.

3. **Read Kodi's log.** The add-on logs every step and yt-dlp's full error message. The log file is `kodi.log` in
   Kodi's user data folder: `~/.kodi/temp/` on Linux, `%APPDATA%\Kodi\` on Windows, `~/Library/Logs/` on macOS,
   `/storage/.kodi/temp/` on LibreELEC and CoreELEC, and reachable through Kore or the Kodi web interface on Android.
   Search for `plugin.video.sendtokodi`. The [Kodi wiki](https://kodi.wiki/view/Log_file) explains how to enable
   debug logging for more detail.

## "Could not resolve the url, check the log for more info"

yt-dlp could not get stream information for the URL. The log has the yt-dlp error right above this message. Typical
reasons:

| Message in the log | Cause and fix |
|---|---|
| `Unsupported URL` | yt-dlp has no extractor for this site. Check the [supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md). Direct links to media files (`.mp4`, `.m3u8`) still play. |
| `Sign in to confirm you're not a bot` | YouTube's bot check. Update yt-dlp (try *Nightly*). If it persists, pass browser cookies through a [yt-dlp config file](settings.md#using-a-yt-dlp-config-file) with `--cookies`. |
| `Requested format is not available`, `No video formats found` | Often a missing JavaScript runtime on YouTube: see [YouTube doesn't play](#youtube-doesnt-play). Otherwise a yt-dlp update. |
| `Video unavailable`, `Private video`, `This video is available to members only` | The site refuses; cookies of a logged-in account may help for private and member content. |
| `HTTP Error 403` | The site blocks the request. Usually fixed by a yt-dlp update; sometimes by cookies or a different `--extractor-args` client. |
| `Could not load yt-dlp config` | The config file has an invalid option. The log names it. |
| `yt-dlp import failed`, `yt-dlp is unavailable` | See [yt-dlp is unavailable](#yt-dlp-is-unavailable). |

## YouTube doesn't play

YouTube needs a JavaScript runtime since 2025. Check *Settings → JavaScript Runtime*:

- **JavaScript runtime mode** must not be *disabled*.
- **Installed Deno version** must show a version. If it shows *not installed*, press **Update Deno now** and watch
  the log for download errors (no internet, no GitHub access, no Deno build for the platform).
- On a Raspberry Pi 2 or 3 with a 32-bit OS, or another ARMv7 device, Deno is not available; use QuickJS, see
  [ARMv7 devices](#armv7-devices-raspberry-pi-2-and-3-32-bit).
- Update yt-dlp as well. YouTube changes often and *Nightly* usually has the fix first.

Only up to 720p plays, or the quality is low: the high qualities need the DASH manifest builder and InputStream
Adaptive. Turn on *Use DASH manifest builder* in *Settings → Adaptive*, run *Check if my Kodi supports adaptive
streaming* and raise **Maximum resolution** if you capped it.

## yt-dlp is unavailable

The add-on could not import yt-dlp:

- With the **Stable** or **Nightly** channel: the download failed. The log shows why (no internet access, GitHub
  unreachable, no space in the profile folder). Press **Update yt-dlp now** to retry. If auto-update is off and you
  declined the download dialog, the add-on asks again after a day; pressing *Update yt-dlp now* installs immediately.
- With the **System** channel: Kodi's Python cannot import `yt_dlp` or one of its dependencies. Install the package
  for the Python Kodi uses, or switch to *Stable*.

## Playback starts but stops, stutters or has no sound

- **No sound or no picture on YouTube:** the manifest builder combined streams Kodi cannot decode, for example an
  AV1 video on a device without AV1 decoding. Lower **Maximum resolution** (lower resolutions use H.264 more often)
  or turn on **Ask which stream to play** and pick an `avc1`/`mp4a` combination.
- **Audio-only HLS stream is silent:** keep **Audio-only HLS: disable Opus for native m3u streams** on; Kodi's HLS
  demuxer cannot play Opus.
- **Playback stops after a pause or a seek:** stream URLs expire. The DASH builder regenerates its manifest after the
  idle timeout; a lower **DASH MPD server idle timeout** makes it refresh sooner.
- **Stutter at high resolutions:** the device cannot decode or the network cannot deliver it. Cap **Maximum
  resolution**, or choose *Adaptive* so InputStream Adaptive adapts to the bandwidth.
- **Stream fails after a few seconds with a 403 in the log:** the site checks headers. A yt-dlp update usually fixes
  it; make sure *Use original manifest* is on, so ISA gets the site's manifest with the matching headers.

## Adaptive streaming checks fail

*Settings → Adaptive → Check if my Kodi supports adaptive streaming* runs InputStream Helper. If it reports that
InputStream Adaptive is missing or disabled, enable it under *Add-ons → My add-ons → VideoPlayer InputStream*; on
Linux distributions it may be a separate package (`kodi-inputstream-adaptive`). Without ISA only progressive formats
play, which means lower quality on most sites.

## ARMv7 devices (Raspberry Pi 2 and 3, 32-bit)

Deno has no 32-bit ARM build, so YouTube does not play with the default runtime on a Raspberry Pi 2 or 3 running a
32-bit OS (LibreELEC for RPi2/3, Raspberry Pi OS 32-bit), or on other ARMv7 boxes. Options:

- **Use a 64-bit OS** if the hardware allows (Raspberry Pi 3 with 64-bit LibreELEC or Raspberry Pi OS), then Deno
  works.
- **Use QuickJS.** Install a `qjs` binary for your platform (from your distribution's packages or a build of
  [QuickJS](https://bellard.org/quickjs/)), set **JavaScript runtime mode** to `quickjs` and enter the path under
  **QuickJS binary path**. In `auto` mode the add-on also prefers QuickJS on ARMv7 as soon as a path is set.

## The client cannot reach Kodi

If the browser extension, the Shortcut or Kore cannot connect, the problem is in Kodi's web server, not in the add-on:

- *Settings → Services → Control → Allow remote control via HTTP* must be on, with a username and password.
- The port is 8080 by default; a firewall on the Kodi device may block it.
- The client and Kodi must be on the same network, and the IP address must be current (give the Kodi device a fixed
  IP in your router).
- Kodi only speaks HTTP. Use HTTPS in a client only if a reverse proxy with a certificate sits in front of Kodi.

The browser extension's [troubleshooting page](https://firsttris.github.io/chrome.sendtokodi/troubleshooting.html)
covers its error messages one by one.

## Kore sends YouTube links to another add-on

Kore remembers a preferred add-on for shared links. Open Kore's settings and set SendToKodi as the add-on for shared
YouTube (and other) links.

## Reporting a bug

Before opening an issue, check that the URL works with yt-dlp outside Kodi (see above). If it does and Kodi still
fails, [open an issue](https://github.com/firsttris/plugin.video.sendtokodi/issues/new/choose) with:

- The URL (or a similar public one, if the original is private)
- Kodi version and platform (for example *Kodi 21 on LibreELEC 12, Raspberry Pi 4*)
- The add-on version and the installed yt-dlp and Deno versions from the settings
- The relevant part of Kodi's log, with debug logging on, as a code block or a paste link

If the URL fails with yt-dlp outside Kodi as well, report it to [yt-dlp](https://github.com/yt-dlp/yt-dlp/issues)
instead; the add-on will pick up the fix automatically with its next yt-dlp update.
