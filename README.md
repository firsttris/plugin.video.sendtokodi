# plugin.video.sendtokodi

:tv: [SendToKodi](https://teufel-it.de/sendtokodi)

- plays various stream [Sites](https://rg3.github.io/youtube-dl/supportedsites.html) links on kodi using [youtube-dl](https://github.com/rg3/youtube-dl)
- create a m3u playlist for your streams
- send stream & playlist links via json-rpc to kodi
- if you send a playlist it will automatically create a playlist in kodi (and starts playing)

### Example Request
```
{
	"jsonrpc": "2.0",
	"method": "Player.Open",
	"params": {
		"item": {
			"file": "plugin://plugin.video.sendtokodi/?https://soundcloud.com/spinnin-deep/sam-feldt-show-me-love-edxs-indian-summer-remix-available-june-1"
		}
	},
	"id": 1
}
```
#### Test with [Postman](https://www.getpostman.com/)

- create new HTTP Request (POST)
- add your endpoint e.g. http://kodi:kodi@192.168.0.138:8080/jsonrpc
- set body to raw - application/json
- add request to body & send

### Example m3u playlist
forge your own custom playlist
```
#EXTM3U
#EXTINF:1,[Youtube] Booka Shade - Body Language
plugin://plugin.video.sendtokodi?https://www.youtube.com/watch?v=TLNdBIRTNM4

#EXTINF:2,[Youtube] Booka Shade - Mardarine Girl
plugin://plugin.video.sendtokodi?https://www.youtube.com/watch?v=BfEa04s8s7M

#EXTINF:3,[Soundcloud] Sam Feldt - Show Me Love
plugin://plugin.video.sendtokodi?https://soundcloud.com/spinnin-deep/sam-feldt-show-me-love-edxs-indian-summer-remix-available-june-1
 
#EXTINF:4,[Youtube] Chop Hop
plugin://plugin.video.sendtokodi?https://www.youtube.com/watch?v=bn3ebh3wkOA
```

### Sources
- https://github.com/rg3/youtube-dl
- https://github.com/ruuk/script.module.youtube.dl
