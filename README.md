# plugin.video.sendtokodi

resolves various video streams using [youtube-dl](https://github.com/rg3/youtube-dl) to play them on kodi

[Supported Sites](https://rg3.github.io/youtube-dl/supportedsites.html)

### Features

- send almost any link or playlist to kodi
- [create a .m3u playlist containing your links](https://github.com/firsttris/plugin.video.sendtokodi/blob/master/playlist-example.m3u)
- [send stream & playlists via json-rpc to kodi](#development)
- call from your Kodi addon
```
xbmc.executebuiltin("ActivateWindow(10025,'plugin://plugin.video.sendtokodi/?<stream_or_playlist_url>',return)")
```

### Apps
- [iOS App](https://itunes.apple.com/de/app/sendtokodi/id1113517603?mt=8) by [Tristan Teufel](https://github.com/firsttris)
- [Android App](https://play.google.com/store/apps/details?id=com.yantcaccia.stk) by [Antonio Cacciapuoti](https://yantcaccia.github.io/)
- [Google Chrome Addon](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf) by [Tristan Teufel](https://github.com/firsttris)
- [MacOS Share Extension](https://github.com/maxgrass/SendToKodi/releases) by [Max Grass](https://github.com/maxgrass)
- [MacOS Share Extension as System Service](https://github.com/anohren/SendToKodi) by [Andreas Öhrén](https://github.com/anohren) forked from Max Grass
	
### Install

Install latest Version:

[Download Repository](https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/repository.sendtokodi-0.0.1.zip)

*Addon is updated continously to always have the latest youtube_dl version*

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
#### Example JSON Request with youtube-dl authentication
```
{
	"jsonrpc": "2.0",
	"method": "Player.Open",
	"params": {
		"item": {
			"file": "plugin://plugin.video.sendtokodi/?https://vk.com/video-124136901_456239025 {\"ydlOpts\":{\"username\":\"user@email.com\",\"password\":\"password with spaces\"}}"
		}
	},
	"id": 1
}
```
Note: ydlOpts object will be passed directly to youtube-dl, so you can pass any [options](https://github.com/rg3/youtube-dl#options) that youtube-dl provides.

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
