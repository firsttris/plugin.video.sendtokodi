# plugin.video.sendtokodi

resolves various video streams using [youtube-dl](https://github.com/rg3/youtube-dl) to play them on kodi

[Supported Sites](https://rg3.github.io/youtube-dl/supportedsites.html)

### Features

- use :tv: [SendToKodi (iOS App)](https://itunes.apple.com/de/app/sendtokodi/id1113517603?mt=8) or :tv: [SendToKodi (Chrome Addon)](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf) or :tv: [SendToKodi (MacOS Share Extension)](https://github.com/maxgrass/SendToKodi/releases) to send almost any link or playlist to kodi
- [create a m3u playlist containing your links](#example-m3u-playlist)
- [send stream & playlists via json-rpc to kodi](#development)

### Install

Install latest Version:

[Download Repository](https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/repository.sendtokodi-0.0.1.zip)

*Addon is updated continously to always have the latest youtube_dl version*

### Example m3u playlist
forge your own custom playlist
[playlist-example.m3u](https://github.com/firsttris/plugin.video.sendtokodi/blob/master/playlist-example.m3u)

### Pyhton Exception
```
TypeError: attribute of type 'NoneType' is not callable
```
[read about cause and workaround](https://github.com/firsttris/repository.sendtokodi/issues/1)

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

:cyclone:

### Sources
- https://github.com/rg3/youtube-dl

## Code of Conduct
See the [CODE](CODE_OF_CONDUCT.md)

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
