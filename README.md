# plugin.video.sendtokodi

[![build-publish-addon](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml/badge.svg)](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml)

This [kodi](https://github.com/xbmc/xbmc) plugin receives URLs and resolves almost all of them with [yt-dlp](https://github.com/yt-dlp/yt-dlp) creating a playable video stream for kodi. The URLs can be send with one of the supported apps listed below. The plugin itself is not in the offical kodi addon repo, to install it with automatic updates you need to add our repo first. Download the repo file for your kodi version and [install it from zip](https://kodi.wiki/view/Add-on_manager). Afterwards the repositoy should be listed and can be selected to install the actual plugin itself. 

[Download repo for kodi 18](https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/repository.sendtokodi-0.0.1.zip)

[Download repo for kodi 19+](https://github.com/firsttris/repository.sendtokodi.python3/raw/master/repository.sendtokodi.python3/repository.sendtokodi.python3-0.0.1.zip)
 
*Please note that kodi 18 is limited to python 2 only, but the used URL resolver yt-dlp requires python 3.6+. Therefore, the kodi 18 version uses [youtube-dl](https://youtube-dl.org/) instead. Unfortunately, the development of youtube-dl is stuck and youtube made breaking changes to their website, resulting in throttled playbacks. The issue has been addressed but due to the absence of maintainers the code is not merged into the project. To enable unthrottled playback [this](https://github.com/ytdl-org/youtube-dl/pull/30184) unofficial version of youtube-dl is used within the plugin instead.*

## Features
- [supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- [create a .m3u playlist](./playlist-example.m3u)
- [send streams or playlists via json-rpc](./docs/DEVELOPMENT.md)
- [call SendToKodi from your Kodi addon](./docs/DEVELOPMENT.md)
- addon is updated automatically


## Supported Apps
- [Kore, Official Remote for Kodi](https://play.google.com/store/apps/details?id=org.xbmc.kore&hl=de&gl=US) by [kodi](https://github.com/xbmc/Kore)
- [SendToKodi iOS App](https://itunes.apple.com/de/app/sendtokodi/id1113517603?mt=8) by [Victoria Teufel](https://github.com/viciteufel)
- [SendToKodi Chrome Addon](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf) by [Tristan Teufel](https://github.com/firsttris)
- [MacOS Share Extension](https://github.com/maxgrass/SendToKodi/releases) by [Max Grass](https://github.com/maxgrass)
- [MacOS Share Extension as System Service](https://github.com/anohren/SendToKodi) by [Andreas Öhrén](https://github.com/anohren) forked from Max Grass
- [Android App](https://play.google.com/store/apps/details?id=com.yantcaccia.stk) by [Antonio Cacciapuoti](https://yantcaccia.github.io/)

## Code of Conduct
See the [CODE](CODE_OF_CONDUCT.md)

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
