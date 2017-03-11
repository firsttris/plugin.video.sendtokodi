### plugin.video.sendtokodi

plays various stream urls on kodi

[Supported Sites](https://rg3.github.io/youtube-dl/supportedsites.html)

- addon gets stream url from JSONRPC request (example below)
- parse stream url using youtube-dl
- add title and thumbnail to xbmc.player()
- play stream

### Example Request

#### [Postman](https://www.getpostman.com/) to Test HTTP Request

- create new HTTP Request POST
- add your endpoint e.g. http://kodi:kodi@20.1.0.138:8080/jsonrpc
- set body to raw (application/json)
- add request to body
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

### Create Playlist
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

###Sources

- https://github.com/ruuk/script.module.youtube.dl
- https://github.com/rg3/youtube-dl