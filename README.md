# plugin.video.sendtokodi

resolves various video streams using [youtube-dl](https://github.com/rg3/youtube-dl) to play them on kodi

[Supported Sites](https://rg3.github.io/youtube-dl/supportedsites.html)

### Features

- use :tv: [SendToKodi (iOS App)](https://itunes.apple.com/de/app/sendtokodi/id1113517603?mt=8) or :tv: [SendToKodi (Chrome Addon)](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf) to send almost any link or playlist to kodi
- [create a m3u playlist containing your links](#Example-m3u-playlist)
- [send stream & playlists via json-rpc to kodi](#Development)

### Install

Install latest Version:
[Download Repository](https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/repository.sendtokodi-0.0.1.zip)
*Addon is updated continously to always have the latest youtube_dl version*

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

### Development
#### Example JSON Request
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

### Continuous integration

[![Build Status](https://travis-ci.org/firsttris/plugin.video.sendtokodi.svg?branch=master)](https://travis-ci.org/firsttris/plugin.video.sendtokodi) 

:dizzy_face:

### Sources
- https://github.com/rg3/youtube-dl

## Donate
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KEAR9ZC228YCL)

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
