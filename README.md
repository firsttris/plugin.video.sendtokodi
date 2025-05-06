# plugin.video.sendtokodi

[![build-publish-addon](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml/badge.svg)](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml)

SendToKodi is a plugin that allows you to send video or audio URLs to [Kodi](https://kodi.tv) and play them. It automatically resolves sent websites into a playable stream using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

![SendToKodi Logo](https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/icon.png)

## Installation

The plugin is not in the official Kodi addon repo. To install it with automatic updates, you need to add our repo first.

1. Download the repo file for your Kodi version:
   - [Kodi 18](https://github.com/firsttris/repository.sendtokodi.leia/raw/master/repository.sendtokodi.leia-1.0.0.zip)
   - [Kodi 19+](https://github.com/firsttris/repository.sendtokodi/raw/refs/heads/master/repository.sendtokodi-1.0.0.zip)
2. [Install the repo from zip](https://kodi.wiki/view/Add-on_manager).
3. The addon `sendtokodi` can be found in the [install from repository](https://kodi.wiki/view/Add-on_manager) section.

*Please note that kodi 18 is internally limited to python2 but the addon uses yt-dlp to resolve URLs which requires python 3.6+. Therefore, the kodi 18 version uses [youtube-dl](https://youtube-dl.org/) instead. Unfortunately, the development of youtube-dl was stuck but it has been resumed. So the kodi 18 version of this plugin might not be as stable as the kodi 19 version.*

## Usage

Once installed, you can send URLs to Kodi using one of the supported apps listed below.

## Apps

### Browser Addons
- [Chrome Store](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf)
- [Mozilla Store](https://addons.mozilla.org/de/firefox/addon/sendtokodi/)
- [Edge Store](https://microsoftedge.microsoft.com/addons/detail/sendtokodi/cfaaejdnkempodfadjkjfblimmakeaij)

For feature requests or to report issues, visit the [Addon Repository](https://github.com/firsttris/chrome.sendtokodi).

### Mobile Apps
- [Kore, Official Andorid Remote for Kodi](https://play.google.com/store/apps/details?id=org.xbmc.kore&hl=de&gl=US)
  - Check the app settings to always use sendtokodi if you get warnings about other missing kodi addons
- The **Official SendToKodi iOS App** has been retired for the time being, but if you have downloaded it before you should be able to do so again from your list of previously purchased apps in iOS App Store.
- [Apple Shortcut](https://raw.githubusercontent.com/firsttris/plugin.video.sendtokodi/refs/heads/master/SendToKodi-OSX.shortcut): This shortcut works on both iOS and macOS. On iOS, it appears in the share sheet when sharing a web address or URL. On macOS, it can be executed directly from the Shortcuts app. Duplicate the shortcut for quick access to all your devices straight from the share sheet.

## Integration
- Supported [Websites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- Ability to [call SendToKodi from a .m3u playlist](./playlist-example.m3u)
- Send Websites to Kodi via [JSON-RPC](./docs/DEVELOPMENT.md#Example-JSON-Request)
- Call SendToKodi from your [Kodi plugin](./docs/DEVELOPMENT.md#Call-SendToKodi-Plugin-from-Kodi)

## Code of Conduct
See the [CODE](CODE_OF_CONDUCT.md)

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
