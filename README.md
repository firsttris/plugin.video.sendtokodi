<div align="center">

# SendToKodi: Play YouTube, Twitch, Vimeo and 1000+ Sites on Kodi

**Send any video link from your browser or phone to Kodi, and watch it on the big screen.**<br>
SendToKodi is a Kodi add-on that turns links from YouTube, Twitch, Vimeo, SoundCloud, Dailymotion and
[1000+ other websites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) into playable streams,
powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

[![Build](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-master.yml/badge.svg)](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-master.yml)
[![Coverage](https://codecov.io/gh/firsttris/plugin.video.sendtokodi/graph/badge.svg)](https://app.codecov.io/gh/firsttris/plugin.video.sendtokodi)
[![Release](https://img.shields.io/github/v/release/firsttris/plugin.video.sendtokodi?label=Release&color=17b2e7)](https://github.com/firsttris/plugin.video.sendtokodi/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE.md)
<br>
[![Kodi 19+](https://img.shields.io/badge/Kodi-19%20%7C%2020%20%7C%2021-17B2E7?logo=kodi&logoColor=white)](https://kodi.tv)
[![Powered by yt-dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-ff0000)](https://github.com/yt-dlp/yt-dlp)
[![Chrome Extension](https://img.shields.io/chrome-web-store/v/gbcpfpcacakaadapjcdchbdmdnfbnbaf?label=Chrome%20Extension&logo=googlechrome&logoColor=white)](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf)
[![Chrome Users](https://img.shields.io/chrome-web-store/users/gbcpfpcacakaadapjcdchbdmdnfbnbaf?label=Chrome%20Users)](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf)
[![Firefox Add-on](https://img.shields.io/amo/v/sendtokodi?label=Firefox%20Add-on&logo=firefox&logoColor=white)](https://addons.mozilla.org/firefox/addon/sendtokodi/)
[![Firefox Users](https://img.shields.io/amo/users/sendtokodi?label=Firefox%20Users)](https://addons.mozilla.org/firefox/addon/sendtokodi/)

[Features](#-features) •
[Install](#-install-in-kodi) •
[Send links](#-send-links-to-kodi) •
[Integration](#-integration) •
[Documentation](https://firsttris.github.io/plugin.video.sendtokodi/) •
[Troubleshooting](#-troubleshooting) •
[FAQ](#-faq)

<img src="https://raw.githubusercontent.com/firsttris/chrome.sendtokodi/master/store-assets/banner/1280x800.png" alt="SendToKodi: send a video from the browser to Kodi" width="800">

</div>

## 💡 Why SendToKodi?

You find a video on your laptop or phone and want to watch it on the TV. With SendToKodi you share the link to
[Kodi](https://kodi.tv) and it plays there, in the best quality the site offers, with Kodi's own player, subtitles
and remote. No casting app, no screen mirroring, no server in between: Kodi fetches the video itself, so your phone
can go to sleep.

It works like a **"cast to Kodi" button for the whole web**: YouTube videos, playlists and channels, Twitch streams
and VODs, Vimeo, SoundCloud, Bandcamp, Reddit, TikTok, the media libraries of public broadcasters, direct links to
media files, and every other site [yt-dlp](https://github.com/yt-dlp/yt-dlp) supports.

## ✨ Features

- 🎬 **Plays 1000+ websites on Kodi**: everything yt-dlp supports, resolved on the Kodi device itself.
- 📺 **Best quality**: adaptive streaming (DASH and HLS) through InputStream Adaptive, up to 4K and 8K, with a built-in
  DASH manifest builder for sites that serve video and audio separately, like YouTube.
- 🔄 **Keeps itself current**: yt-dlp and the Deno JavaScript runtime are downloaded and updated automatically, with
  a nightly channel for site fixes weeks before the next release and a version switcher to roll back.
- 📋 **Playlists and queue**: send a whole playlist or channel, or queue videos one by one without interrupting
  playback.
- 🌐 **Send from anywhere**: browser extension for Chrome, Firefox and Edge, Kore on Android, an Apple Shortcut on
  iPhone and Mac, or any JSON-RPC call from scripts and Home Assistant.
- 💬 **Subtitles, title and artwork** from the website appear in Kodi's player.
- 💾 **Optional download** before playback, for unstable connections or to keep a copy.
- 🔐 **Logins and options**: a yt-dlp config file for cookies, proxies and extractor arguments, or per-request
  options over JSON-RPC.
- 🆓 **Free and open source** (MIT), no tracking, nothing in between you and the website.

## 📦 Install in Kodi

Requires **Kodi 19 or newer** on any platform: Windows, Linux, macOS, Android, Android TV, Fire TV, LibreELEC,
CoreELEC. The add-on is not in the official Kodi repository, so install the SendToKodi repository first; it keeps
the add-on updated automatically.

1. Download [repository.sendtokodi-1.0.0.zip](https://github.com/firsttris/repository.sendtokodi/raw/refs/heads/master/repository.sendtokodi-1.0.0.zip)
   to a place your Kodi can reach.
2. In Kodi, go to **Add-ons → Install from zip file** and install the ZIP (allow *Unknown sources* once if Kodi asks).
3. Go to **Add-ons → Install from repository → SendToKodi Repository → Video add-ons** and install **SendToKodi**.

On the first playback, the add-on downloads yt-dlp and, for YouTube, the Deno JavaScript runtime. Details, including
manual installation, updating and the first start:
[Installation guide](https://firsttris.github.io/plugin.video.sendtokodi/installation.html).

## 📱 Send links to Kodi

The add-on receives links; one of these sends them:

| From | With | Get it |
|---|---|---|
| **Chrome, Edge, Brave, Vivaldi, Opera** | SendToKodi browser extension: one click, keyboard shortcut or right-click *Play on Kodi* | [Chrome Web Store](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf) · [Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/sendtokodi/cfaaejdnkempodfadjkjfblimmakeaij) |
| **Firefox** | SendToKodi browser extension | [Mozilla Add-ons](https://addons.mozilla.org/firefox/addon/sendtokodi/) |
| **Android** | Kore, the official Kodi remote, via the share menu | [Google Play](https://play.google.com/store/apps/details?id=org.xbmc.kore) |
| **iPhone, iPad, Mac** | Apple Shortcut via the share sheet | [SendToKodi-OSX.shortcut](https://raw.githubusercontent.com/firsttris/plugin.video.sendtokodi/refs/heads/master/SendToKodi-OSX.shortcut) |
| **Scripts, Home Assistant, playlists** | Kodi's JSON-RPC API or a `plugin://` URL | [Integration](#-integration) |

The browser extension has its own repository and documentation:
[firsttris/chrome.sendtokodi](https://github.com/firsttris/chrome.sendtokodi) ·
[firsttris.github.io/chrome.sendtokodi](https://firsttris.github.io/chrome.sendtokodi/).

## ⚙️ Settings

Open them in Kodi via **Add-ons → My add-ons → Video add-ons → SendToKodi → Configure**. The important ones:

- **yt-dlp release channel** (*Stable*, *Nightly*, *System*) and **Update yt-dlp now**: a site that stopped working is
  usually fixed by a newer yt-dlp, and *Nightly* gets fixes first.
- **JavaScript runtime mode**: YouTube needs a JavaScript runtime; the add-on manages Deno, with QuickJS as the option
  for 32-bit ARM devices.
- **yt-dlp config file**: cookies for logins, proxies, extractor arguments, in yt-dlp's own format.
- **Maximum resolution**, **Ask which stream to play** and the **DASH manifest builder** under *Adaptive*.
- **Auto-download resolved media before playback** and the download path.

Every setting is explained in the [settings reference](https://firsttris.github.io/plugin.video.sendtokodi/settings.html).

## 🔌 Integration

Anything that can make Kodi play a `plugin://` URL can use SendToKodi: JSON-RPC, M3U playlists, STRM files, other
add-ons, Home Assistant.

```json
{
  "jsonrpc": "2.0",
  "method": "Player.Open",
  "params": {
    "item": {
      "file": "plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DTLNdBIRTNM4"
    }
  },
  "id": 1
}
```

Send it as a `POST` to `http://<kodi-ip>:8080/jsonrpc` with Kodi's web server credentials. Add `action=queue` to
queue instead of play, and `yt-dlp-options` with a JSON object for per-request yt-dlp options such as a login. The
full URL format, `curl` and Python examples, playlists, STRM files and Home Assistant are in the
[integration guide](https://firsttris.github.io/plugin.video.sendtokodi/integration.html).

## 🧰 Troubleshooting

- **A video doesn't play:** update yt-dlp (*Settings → yt-dlp → Update yt-dlp now*), try the *Nightly* channel, and
  check the URL with `yt-dlp --simulate "<url>"` outside Kodi. If yt-dlp fails there too, the fix has to come from
  yt-dlp; the add-on picks it up automatically.
- **YouTube doesn't play:** make sure *Installed Deno version* shows a version and the runtime mode is not *disabled*.
  On a 32-bit Raspberry Pi 2 or 3, use QuickJS.
- **Only 720p on YouTube:** turn on the DASH manifest builder and raise *Maximum resolution*.
- **The extension or app can't reach Kodi:** enable *Allow remote control via HTTP* in Kodi's
  *Settings → Services → Control*.

More in the [troubleshooting guide](https://firsttris.github.io/plugin.video.sendtokodi/troubleshooting.html), with
the log location and the common yt-dlp error messages.

## ❓ FAQ

**Which sites work?** Everything on [yt-dlp's list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md),
plus direct links to media files. DRM-protected services (Netflix, Disney+, Prime Video) do not work.

**Is this like Chromecast?** Similar in effect: the link goes to Kodi and Kodi fetches the video itself. Your phone or
laptop is not involved in the playback.

**Why isn't it in the official Kodi repository?** The official repository doesn't allow add-ons that download code
at runtime, and SendToKodi has to update yt-dlp on its own to keep up with the websites.

**Does it work on Android TV, Fire TV, Raspberry Pi?** Yes, on every platform Kodi 19+ runs on. Only the YouTube
JavaScript runtime needs a 64-bit system or QuickJS.

More answers in the [FAQ](https://firsttris.github.io/plugin.video.sendtokodi/faq.html).

## 📖 Documentation

The full documentation is at **[firsttris.github.io/plugin.video.sendtokodi](https://firsttris.github.io/plugin.video.sendtokodi/)**:
[installation](https://firsttris.github.io/plugin.video.sendtokodi/installation.html),
[usage](https://firsttris.github.io/plugin.video.sendtokodi/usage.html),
[settings](https://firsttris.github.io/plugin.video.sendtokodi/settings.html),
[integration](https://firsttris.github.io/plugin.video.sendtokodi/integration.html),
[how it works](https://firsttris.github.io/plugin.video.sendtokodi/how-it-works.html),
[troubleshooting](https://firsttris.github.io/plugin.video.sendtokodi/troubleshooting.html) and
[development](https://firsttris.github.io/plugin.video.sendtokodi/development.html). The source is in
[docs/](docs/README.md).

## 💻 Development

```bash
git clone https://github.com/firsttris/plugin.video.sendtokodi.git
cd plugin.video.sendtokodi
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest
```

The logic lives in `core/` and is unit-tested without Kodi; `service.py` is the entry point Kodi runs. Symlink the
checkout into Kodi's `addons` folder to run it. Setup, project structure, CI and the release process:
[Development](https://firsttris.github.io/plugin.video.sendtokodi/development.html).

## 🤝 Contributing

Bug reports, ideas and pull requests are welcome. Before reporting a site that doesn't play, check it with yt-dlp
outside Kodi; if it fails there, [yt-dlp's issues](https://github.com/yt-dlp/yt-dlp/issues) are the right place.

## 📄 License

[MIT](LICENSE.md). Kodi is a trademark of the XBMC Foundation; this project is not affiliated with the XBMC
Foundation or yt-dlp.

---

<div align="center">

⭐ Like SendToKodi? [Star it on GitHub](https://github.com/firsttris/plugin.video.sendtokodi) •
🐛 [Report a bug](https://github.com/firsttris/plugin.video.sendtokodi/issues) •
💡 [Request a feature](https://github.com/firsttris/plugin.video.sendtokodi/issues)

</div>
