---
description: Integrate SendToKodi via Kodi JSON-RPC, the plugin:// URL, yt-dlp options per request, the queue action, M3U playlists, STRM files, other Kodi add-ons, Home Assistant and shell scripts with curl.
---

# API & integration

SendToKodi has no API of its own: it is a Kodi plugin, so anything that can make Kodi play a `plugin://` URL can use
it. That includes Kodi's JSON-RPC interface, playlists, STRM files, other add-ons, Home Assistant and a shell with
`curl`. This page documents the URL format and shows the common clients.

## The plugin URL

```text
plugin://plugin.video.sendtokodi/?url=<url-encoded media URL>
```

| Parameter | Required | Meaning |
|---|---|---|
| `url` | yes | The web page or media URL to resolve, URL-encoded (`https://` becomes `https%3A%2F%2F`). Anything in yt-dlp's [list of supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) works, and direct links to media files play as well. Playlist and channel URLs are expanded into Kodi's playlist. |
| `yt-dlp-options` | no | A URL-encoded JSON object with [yt-dlp options](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L200) for this request only, for example credentials or extractor arguments. The legacy key `ydlOpts` is still accepted. See [yt-dlp options per request](#yt-dlp-options-per-request). |
| `action` | no | `queue` appends the item to Kodi's playlist instead of playing it. See [Queue instead of play](#queue-instead-of-play). |
| `title` | with `action=queue` | Label of the queued item, URL-encoded. Without it the URL is shown. `name` is accepted as an alias. |

### Legacy form

Older integrations put the media URL directly after the `?`, without `url=` and without encoding:

```text
plugin://plugin.video.sendtokodi/?https://www.youtube.com/watch?v=TLNdBIRTNM4
```

This still works and is what the browser extension sends for *Play*. It cannot carry other parameters, except for the
old form of yt-dlp options: a space followed by a JSON object `{"ydlOpts": {...}}`. New integrations should use the
`url=` form, which survives any characters in the target URL.

## JSON-RPC

Kodi's [JSON-RPC API](https://kodi.wiki/view/JSON-RPC_API) is reachable over HTTP once *Settings → Services → Control →
Allow remote control via HTTP* is on. The endpoint is `http://<kodi-ip>:8080/jsonrpc` with the username and password
from the same settings page as HTTP basic auth. To play a URL, call `Player.Open` with the plugin URL as the file:

```json
{
  "jsonrpc": "2.0",
  "method": "Player.Open",
  "params": {
    "item": {
      "file": "plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fsoundcloud.com%2Fspinnin-deep%2Fsam-feldt-show-me-love-edxs-indian-summer-remix-available-june-1"
    }
  },
  "id": 1
}
```

With `curl`:

```bash
curl -u kodi:kodi -H 'Content-Type: application/json' http://192.168.0.138:8080/jsonrpc -d '{
  "jsonrpc": "2.0", "id": 1, "method": "Player.Open",
  "params": {"item": {"file": "plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DTLNdBIRTNM4"}}
}'
```

Kodi answers `{"id":1,"jsonrpc":"2.0","result":"OK"}` as soon as it has accepted the item; resolving happens afterwards
inside Kodi, so a failing URL is reported on the Kodi screen and in its log, not in the JSON-RPC response.

### Testing with Postman or similar tools

1. Create a `POST` request to `http://<user>:<password>@<kodi-ip>:8080/jsonrpc`.
2. Set the body type to raw `application/json`.
3. Paste one of the JSON-RPC examples and send.

## yt-dlp options per request

`yt-dlp-options` carries a JSON object that is merged into the options yt-dlp runs with, for this request only. Any
option of yt-dlp's Python API is accepted; the names are those of `YoutubeDL`'s options, not the command line flags.
Typical use is a site login:

```json
{
  "jsonrpc": "2.0",
  "method": "Player.Open",
  "params": {
    "item": {
      "file": "plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fvk.com%2Fvideo-124136901_456239025&yt-dlp-options=%7B%22username%22%3A%22user%40email.com%22%2C%22password%22%3A%22password%20with%20spaces%22%7D"
    }
  },
  "id": 1
}
```

Decoded, the `yt-dlp-options` value is `{"username": "user@email.com", "password": "password with spaces"}`. Options
that apply to every request belong into the [yt-dlp config file](settings.md#using-a-yt-dlp-config-file) instead.
Request options win over the config file, and both win over the add-on's own defaults.

## Queue instead of play

`action=queue` adds the item to Kodi's video playlist without interrupting the current playback. If nothing is playing,
the item waits in the playlist until you start it. `title` sets the label shown in the playlist:

```text
plugin://plugin.video.sendtokodi/?action=queue&url=<url-encoded URL>&title=<url-encoded title>
```

Via JSON-RPC, send it with `Player.Open` just like a playback request; the add-on recognises the action and queues
instead of playing. From inside Kodi or another add-on, `RunPlugin` does the same:

```python
xbmc.executebuiltin("RunPlugin(plugin://plugin.video.sendtokodi/?action=queue&url=<urlencoded_stream_url>&title=<urlencoded_title>)")
```

The queued entry is resolved when it is reached, so queuing is instant and a site that fails to resolve only affects
its own entry.

## Playlists and STRM files

Kodi's own playlists and library accept plugin URLs. An M3U file with website links
([playlist-example.m3u](https://github.com/firsttris/plugin.video.sendtokodi/blob/master/playlist-example.m3u) in the
repository):

```m3u
#EXTM3U
#EXTINF:1,[Youtube] Booka Shade - Body Language
plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DTLNdBIRTNM4

#EXTINF:2,[Soundcloud] Sam Feldt - Show Me Love
plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fsoundcloud.com%2Fspinnin-deep%2Fsam-feldt-show-me-love-edxs-indian-summer-remix-available-june-1
```

A `.strm` file contains one plugin URL and behaves like a video file in Kodi's library. Combined with an NFO file for
the metadata, website videos can be part of a library section.

## From another Kodi add-on

Any add-on can hand a URL to SendToKodi. To play it immediately:

```python
import urllib.parse
import xbmc

url = urllib.parse.quote("https://www.youtube.com/watch?v=TLNdBIRTNM4", safe="")
xbmc.executebuiltin("PlayMedia(plugin://plugin.video.sendtokodi/?url={})".format(url))
```

`ActivateWindow(10025, 'plugin://plugin.video.sendtokodi/?url=...', return)` is the older form found in existing
add-ons and keeps working. To list a SendToKodi item in your own directory, create a `ListItem` with the plugin URL as
its path and `IsPlayable` set to `true`; Kodi resolves it through SendToKodi when the user selects it.

## Home Assistant and other automation

Home Assistant's [Kodi integration](https://www.home-assistant.io/integrations/kodi/) exposes the JSON-RPC API as the
`kodi.call_method` action, so an automation or a script can send any link to Kodi:

```yaml
action: kodi.call_method
target:
  entity_id: media_player.kodi_living_room
data:
  method: Player.Open
  item:
    file: "plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DTLNdBIRTNM4"
```

Node-RED, openHAB, ioBroker and similar systems have Kodi nodes or bindings that send JSON-RPC in the same way. Any
HTTP client works as well, as the `curl` example above shows.

## Behaviour to rely on

- **Resolving is asynchronous.** JSON-RPC returns before the URL is resolved. Watch Kodi's player state
  (`Player.GetActivePlayers`) or its notifications to know whether playback started.
- **Playlists expand lazily.** A playlist URL adds all entries at once but resolves each entry when it is played.
- **Errors show on screen.** A failed resolve shows *Could not resolve the url* in Kodi and writes the yt-dlp
  traceback to Kodi's log. There is no error channel back to the sender.
- **Encoding matters.** In the `url=` form, encode the target URL completely (`urllib.parse.quote(url, safe="")` in
  Python, `encodeURIComponent` in JavaScript). An unencoded `&` in the target URL would be read as a plugin parameter.
