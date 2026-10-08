---
description: Frequently asked questions about SendToKodi. Which sites work, does it cast like Chromecast, is it free, does it work on Android TV, Fire TV, Raspberry Pi, LibreELEC and CoreELEC, how to play YouTube on Kodi without ads.
---

# FAQ

## Which websites work?

Everything [yt-dlp supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md), over a thousand sites:
YouTube, Twitch (VODs and live streams), Vimeo, Dailymotion, SoundCloud, Bandcamp, Reddit, Twitter/X, TikTok,
Instagram, Facebook videos, the media libraries of many public broadcasters (ARD, ZDF, arte, BBC iPlayer with cookies,
…) and direct links to media files. DRM-protected services (Netflix, Disney+, Amazon Prime Video, Spotify) do not work
and never will; yt-dlp does not bypass DRM.

## Is this like casting with Chromecast?

Similar in effect, different in mechanism. Chromecast receives a stream from the sending device or a cloud service.
SendToKodi only sends the link to Kodi; Kodi fetches the video itself, directly from the website. The sending device
can go to sleep, playback continues, and Kodi's own player handles it, with its subtitle, audio and quality settings.

## Does it play YouTube without ads?

Kodi plays the streams yt-dlp picks, which contain no ad breaks. SponsorBlock and similar are not integrated.

## Is it free? Is there tracking?

SendToKodi is free and open source under the MIT license. The add-on talks to the website you send, to GitHub for
yt-dlp and Deno updates, and to nothing else. The browser extension has its own
[privacy policy](https://github.com/firsttris/chrome.sendtokodi/blob/master/PRIVACY.md): no tracking, no server in
between.

## Which Kodi versions and platforms are supported?

Kodi 19 and newer, on every platform Kodi runs on: Windows, Linux, macOS, Android (including Android TV and Fire TV),
LibreELEC and CoreELEC. The only restriction is the JavaScript runtime for YouTube: Deno needs a 64-bit system, so on a
32-bit Raspberry Pi 2 or 3 you need [QuickJS](troubleshooting.md#armv7-devices-raspberry-pi-2-and-3-32-bit).

## Why isn't it in the official Kodi repository?

The official repository forbids add-ons that download and run code at runtime. SendToKodi has to update yt-dlp and
Deno on its own, because yt-dlp needs updates every few weeks to keep up with the websites, and that is not possible
through the official repository's release process. The
[SendToKodi repository](installation.md#install-from-the-sendtokodi-repository-recommended) gives you automatic
updates anyway.

## Do I need the browser extension?

No. The extension is the most convenient way to send links from a desktop browser, but Kore on Android, the Shortcut on
iPhone and Mac, or any JSON-RPC call do the same. See [Usage](usage.md).

## Can I queue several videos?

Yes. The browser extension has *Add to Queue* and the context menu entry *Add to Kodi queue*; clients use the
[`action=queue`](integration.md#queue-instead-of-play) parameter. Playlist and channel URLs are also expanded into
Kodi's playlist.

## Can I download videos instead of streaming them?

Yes, turn on *Auto-download resolved media before playback* in the settings. The file is downloaded to the configured
folder first and then played from disk. See [Downloading instead of streaming](usage.md#downloading-instead-of-streaming).

## How do I log in to a website?

Export your browser's cookies for that site and point the add-on to the file with `--cookies` in a
[yt-dlp config file](settings.md#using-a-yt-dlp-config-file). For a single request, credentials can also be passed as
[yt-dlp options](integration.md#yt-dlp-options-per-request).

## Something stopped working that worked yesterday

Update yt-dlp (*Settings → yt-dlp → Update yt-dlp now*), and switch to the *Nightly* channel if the stable release
doesn't help yet. Websites change, yt-dlp follows, the add-on follows yt-dlp. See [Troubleshooting](troubleshooting.md).

## How do I contribute?

Bug reports and pull requests are welcome on [GitHub](https://github.com/firsttris/plugin.video.sendtokodi).
[Development](development.md) explains the setup and the tests.
