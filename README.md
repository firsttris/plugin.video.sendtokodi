# plugin.video.sendtokodi

:tv: [SendToKodi](https://teufel-it.de/sendtokodi)

- plays various stream [sites](https://rg3.github.io/youtube-dl/supportedsites.html) on kodi using [youtube-dl](https://github.com/rg3/youtube-dl)
- create a m3u playlist containing your links
- send stream & playlist links via json-rpc to kodi
- if you send a playlist it will automatically create a playlist and starts playing

### Install

1. Click "Clone or Download" in the upper right corner
2. Click "Download ZIP"
3. (in Kodi) Install Addon via Zip File

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
#EXTINF:1,[Youtube] Track1
plugin://plugin.video.sendtokodi?https://www.youtube.com/watch?v=<url>

#EXTINF:2,[Youtube] Track2
plugin://plugin.video.sendtokodi?https://www.youtube.com/watch?v=<url>

#EXTINF:3,[Soundcloud] Track3
plugin://plugin.video.sendtokodi?https://soundcloud.com/<url>
 
#EXTINF:4,[Youtube] Track4
plugin://plugin.video.sendtokodi?https://www.youtube.com/watch?v=<url>
```

### Sources
- https://github.com/rg3/youtube-dl
- https://github.com/ruuk/script.module.youtube.dl

## Donate
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KEAR9ZC228YCL)

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
