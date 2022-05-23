
# Development
## Example JSON Request
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
## Example JSON Request with youtube-dl authentication
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

## Call SendToKodi Plugin from Kodi

```
xbmc.executebuiltin("ActivateWindow(10025,'plugin://plugin.video.sendtokodi/?<stream_or_playlist_url>',return)")
```

## Test with [Postman](https://www.getpostman.com/)

- create new HTTP Request (POST)
- add your endpoint e.g. http://kodi:kodi@192.168.0.138:8080/jsonrpc
- set body to raw - application/json
- add request to body & send