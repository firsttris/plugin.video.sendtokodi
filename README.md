# plugin.video.sendtokodi

[![build-publish-addon](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml/badge.svg)](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml)

This add-on receives video or audio URLs and plays them in [Kodi](https://kodi.tv). It resolves sent websites automatically with [yt-dlp](https://github.com/yt-dlp/yt-dlp) into a playable stream. The URLs can be sent with one of the supported apps listed below. 

<img src="https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/icon.png" alt="drawing" width="200"/>


## Installation 
The plugin is not in the offical kodi addon repo, to install it with automatic updates you need to add our repo first. Download the repo file for your kodi version and [install the repo from zip](https://kodi.wiki/view/Add-on_manager). Afterwards the addon `sendtokodi` can be found in the [install from repository](https://kodi.wiki/view/Add-on_manager) section.

[Download repo for kodi 18](https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/repository.sendtokodi-0.0.1.zip)

[Download repo for kodi 19+](https://github.com/firsttris/repository.sendtokodi.python3/raw/master/repository.sendtokodi.python3/repository.sendtokodi.python3-1.0.0.zip)
 
*Please note that kodi 18 is internally limited to python2 but the addon uses yt-dlp to resolve URLs which requires python 3.6+. Therefore, the kodi 18 version uses [youtube-dl](https://youtube-dl.org/) instead. Unfortunately, the development of youtube-dl was stuck but it has been resumed. So the kodi 18 version of this plugin might not be as stable as the kodi 19 version.*

## Features
- [supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- [create a .m3u playlist](./playlist-example.m3u)
- [send streams or playlists via json-rpc](./docs/DEVELOPMENT.md)
- [call SendToKodi from your Kodi addon](./docs/DEVELOPMENT.md)
- addon is updated automatically


## Supported Apps
- [Kore, Official Andorid Remote for Kodi](https://play.google.com/store/apps/details?id=org.xbmc.kore&hl=de&gl=US) by [kodi](https://github.com/xbmc/Kore)
  - Check the app settings to always use sendtokodi if you get warnings about other missing kodi addons  
- [SendToKodi iOS App](https://itunes.apple.com/de/app/sendtokodi/id1113517603?mt=8) by [Victoria Teufel](https://github.com/viciteufel)
- [SendToKodi Chrome Addon](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf) by [Tristan Teufel](https://github.com/firsttris)
- [MacOS Share Extension](https://github.com/maxgrass/SendToKodi/releases) by [Max Grass](https://github.com/maxgrass)
- [MacOS Share Extension as System Service](https://github.com/anohren/SendToKodi) by [Andreas Öhrén](https://github.com/anohren) forked from Max Grass
- [Android App](https://play.google.com/store/apps/details?id=com.yantcaccia.stk) by [Antonio Cacciapuoti](https://yantcaccia.github.io/)

## Code of Conduct
See the [CODE](CODE_OF_CONDUCT.md)

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
