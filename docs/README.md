---
description: Documentation for the SendToKodi Kodi add-on. Install it, send videos from your browser or phone to Kodi, configure yt-dlp, Deno and adaptive streaming, integrate it via JSON-RPC.
---

# SendToKodi documentation

SendToKodi is a [Kodi](https://kodi.tv) add-on that plays video and audio from **YouTube, Twitch, Vimeo, SoundCloud,
Dailymotion and [1000+ other websites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)** on your Kodi
media center. You send a link from your browser, your Android phone or your iPhone, and Kodi plays it on the big
screen. Under the hood, [yt-dlp](https://github.com/yt-dlp/yt-dlp) resolves the website into a playable stream.

This site has the details: how to install and configure the add-on, how to send links from every device, how to call
it from playlists, other add-ons or any JSON-RPC client, and how it works inside. For the quick overview, see the
[README on GitHub](https://github.com/firsttris/plugin.video.sendtokodi#readme).

## Users

| | |
|---|---|
| [Installation](installation.md) | Requirements, the SendToKodi repository for automatic updates, manual installation, first start, updating, uninstalling |
| [Usage](usage.md) | Sending links from the browser extension, from Android (Kore), from iPhone and Mac (Shortcut), playlists, the queue, choosing a stream, subtitles, downloads |
| [Settings](settings.md) | Every setting explained: General, JavaScript runtime, yt-dlp, Adaptive |
| [Troubleshooting](troubleshooting.md) | What to do when a video doesn't play, where the log is, YouTube and bot checks, cookies, ARMv7 devices |
| [FAQ](faq.md) | Short answers to the most common questions |

## Integration

| | |
|---|---|
| [API & integration](integration.md) | The `plugin://` URL, JSON-RPC requests, yt-dlp options per request, the queue, M3U playlists and STRM files, calling SendToKodi from another add-on, Home Assistant and scripts |

## Background

| | |
|---|---|
| [How it works](how-it-works.md) | Architecture, the resolve-and-play flow, managed yt-dlp and Deno runtimes, the DASH manifest builder, stream selection, files on disk |
| [Development](development.md) | Local setup, unit tests and coverage, project structure, running the add-on from a checkout, releases, writing documentation |

## The companion apps

The add-on does the work inside Kodi. To send links to it you use one of these:

- **Browser extension** for Chrome, Firefox, Edge and other Chromium browsers:
  [chrome.sendtokodi](https://github.com/firsttris/chrome.sendtokodi), with its own
  [documentation](https://firsttris.github.io/chrome.sendtokodi/).
- **Kore**, the official Kodi remote for Android, through the Android share menu.
- **Apple Shortcut** for iPhone, iPad and Mac, through the iOS share sheet.
- **Anything that speaks JSON-RPC**: scripts, Home Assistant, playlists in Kodi itself.

All of them are described in [Usage](usage.md).
