---
description: Send YouTube, Twitch or any video link to Kodi from Chrome, Firefox, Edge, Android (Kore) or iPhone (Shortcut). Play, queue, choose a stream, use playlists, subtitles and downloads with SendToKodi.
---

# Usage

Once the add-on is installed, every way of using it comes down to the same thing: a URL reaches the add-on, yt-dlp
resolves it, Kodi plays it. This page shows the ways to send that URL and what happens during playback.

## From the browser

The [SendToKodi browser extension](https://github.com/firsttris/chrome.sendtokodi) for Chrome, Firefox, Edge and
other Chromium browsers is the most comfortable way. After entering your Kodi's address once:

- Click the toolbar icon on a video page and press **Play**. The URL of the current tab is already filled in.
- Press `Alt+Shift+K` to play the current tab or `Alt+Shift+Q` to add it to Kodi's queue, without opening the popup.
- Right-click a link, a video or a page and choose **Play on Kodi** or **Add to Kodi queue**.
- Keep several Kodi devices (living room, bedroom, …) and switch between them in the popup.

Setup and troubleshooting of the extension are in its own documentation:
[firsttris.github.io/chrome.sendtokodi](https://firsttris.github.io/chrome.sendtokodi/).

## From Android

[Kore](https://play.google.com/store/apps/details?id=org.xbmc.kore), the official Kodi remote, sends shared links to
SendToKodi:

1. Install Kore and connect it to your Kodi (it finds Kodi on the local network when *Allow remote control via HTTP*
   is on).
2. In any app, open the share menu of a video (the YouTube app, a browser, a chat message) and choose **Kore**.
3. If Kore asks which add-on should handle the link, choose **SendToKodi**. Kore remembers the choice; it can be
   changed later in Kore's settings.

If a YouTube link opens a different add-on, set SendToKodi as the preferred add-on in Kore's settings.

## From iPhone, iPad and Mac

The official iOS SendToKodi app is retired. The
[SendToKodi Shortcut](https://raw.githubusercontent.com/firsttris/plugin.video.sendtokodi/refs/heads/master/SendToKodi-OSX.shortcut)
replaces it on iOS and macOS:

1. Open the link on the device; the Shortcuts app offers to add the shortcut.
2. Put the address of your Kodi web server (`http://<ip>:8080`), the username and the password from
   *Settings → Services → Control* in Kodi into the shortcut (the Shortcuts app shows its settings when you add it, and
   you can edit them any time).
3. Share a video from Safari, the YouTube app or any other app and pick **SendToKodi** in the share sheet.

The shortcut sends the same JSON-RPC request the browser extension sends (see [Integration](integration.md)), so it
works with any link yt-dlp supports.

## From Kodi itself

Opening the add-on in Kodi's add-on list (*Add-ons → Video add-ons → SendToKodi*) opens its settings: the add-on has no
browsing interface, since it only plays what it is given. To play a link from inside Kodi, put it into a playlist or a
STRM file as described in [Playlists and STRM files](#playlists-and-strm-files).

## What happens on playback

1. A progress dialog *Resolving …* appears while yt-dlp fetches the page and the stream information. This takes a
   second or two; sites with a JavaScript challenge (YouTube) take a little longer the first time because the
   JavaScript runtime starts.
2. The add-on picks a stream (see [Stream selection](#stream-selection)) and hands it to Kodi. Adaptive streams play
   through InputStream Adaptive and show quality switching in Kodi's player settings.
3. Title, description and thumbnail from the website appear in Kodi's player info. Subtitles the site offers are
   downloaded and selectable in the player.

If anything fails, a notification *Could not resolve the url* appears and the reason is in Kodi's log; see
[Troubleshooting](troubleshooting.md).

## Playlists and the queue

**Playlists on the website.** A YouTube playlist, a SoundCloud set or a channel URL is sent like a single video. The
add-on resolves the playlist, adds every entry to Kodi's video playlist and starts the first one. Each entry resolves
itself only when its turn comes, so long playlists start quickly.

**Kodi's queue.** Instead of interrupting what is playing, a link can be appended to Kodi's current playlist. The
browser extension does this with *Add to Queue* (`Alt+Shift+Q`) and the context menu entry *Add to Kodi queue*. Other
clients use the `action=queue` parameter of the plugin URL, see [Integration](integration.md#queue-instead-of-play).

**Your own M3U playlists** in Kodi can mix website links with local files, see
[Playlists and STRM files](#playlists-and-strm-files).

## Stream selection

Most sites offer several qualities and formats. By default the add-on chooses on its own:

- Adaptive streams (DASH, HLS) are preferred whenever InputStream Adaptive is available, because they let Kodi switch
  quality during playback and deliver the highest resolutions.
- Separate video and audio streams, as YouTube serves them, are combined into a DASH manifest by the add-on's
  [manifest builder](how-it-works.md#the-dash-manifest-builder).
- **Maximum resolution** in the settings caps the video width. The default is 1920 pixels (Full HD); choose *Adaptive*
  to let InputStream Adaptive decide by bandwidth, or 4K or 8K if your Kodi can play it.

Turn on **Ask which stream to play** in *Settings → Adaptive* to pick the stream yourself for every playback. The
dialog lists each format yt-dlp found with resolution, codecs and container. This is useful for audio-only playback
(choose an audio stream) or to work around a format Kodi cannot decode.

## Subtitles

Subtitles the website offers (for example YouTube's manual captions) are downloaded to the add-on's data folder and
attached to the playback, so they appear in Kodi's subtitle menu. Automatic captions are not fetched. The files are
downloaded again on every playback, since the subtitle URLs of most sites expire.

## Downloading instead of streaming

**Auto-download resolved media before playback** in *Settings → General* makes the add-on download the media file
first and play the local file afterwards. This helps on slow or unstable connections, with streams that expire quickly,
and when Kodi should keep a copy. A progress dialog shows the download. The target folder is **Media download path**,
by default `special://profile/addon_data/plugin.video.sendtokodi/downloads`; any Kodi path works, including network
shares. A playlist is not downloaded as a whole: each video is downloaded when its turn comes.

## Playlists and STRM files

Kodi plays any `plugin://` URL from an M3U playlist or a `.strm` file, so website links can live next to your own
media library:

```m3u
#EXTM3U
#EXTINF:1,[Youtube] Booka Shade - Body Language
plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DTLNdBIRTNM4

#EXTINF:2,[Soundcloud] Sam Feldt - Show Me Love
plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fsoundcloud.com%2Fspinnin-deep%2Fsam-feldt-show-me-love-edxs-indian-summer-remix-available-june-1
```

A `.strm` file holds a single such line. Put it into a folder Kodi scans and the video shows up in the library like a
local file; the link is resolved when you play it. See [Integration](integration.md#the-plugin-url) for the exact URL
format, including the legacy form without `url=` that older playlists use.
