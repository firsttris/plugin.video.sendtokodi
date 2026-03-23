# plugin.video.sendtokodi

[![build-publish-addon](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml/badge.svg)](https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml)

SendToKodi is a plugin that allows you to send video or audio URLs to [Kodi](https://kodi.tv) and play them. It automatically resolves sent websites into a playable stream using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

![SendToKodi Logo](https://github.com/firsttris/repository.sendtokodi/raw/master/repository.sendtokodi/icon.png)

## Installation

The plugin is not in the official Kodi addon repo. To install it with automatic updates, you need to add our repo first.

1. Download the repo file for your Kodi version:
   - [Kodi 19+](https://github.com/firsttris/repository.sendtokodi/raw/refs/heads/master/repository.sendtokodi-1.0.0.zip)
2. [Install the repo from zip](https://kodi.wiki/view/Add-on_manager).
3. The addon `sendtokodi` can be found in the [install from repository](https://kodi.wiki/view/Add-on_manager) section.

### Local Development Installation

To test local changes from this repository in Kodi, use one of these methods:

1. **Symlink (recommended for active development)**
  ```bash
  # Standard Kodi install
  rm -rf ~/.kodi/addons/plugin.video.sendtokodi
  ln -s /home/tristan/Projects/plugin.video.sendtokodi ~/.kodi/addons/plugin.video.sendtokodi

  # Flatpak Kodi install
  rm -rf /home/tristan/.var/app/tv.kodi.Kodi/data/addons/plugin.video.sendtokodi
  ln -s /home/tristan/Projects/plugin.video.sendtokodi /home/tristan/.var/app/tv.kodi.Kodi/data/addons/plugin.video.sendtokodi
  ```
  Restart Kodi (or disable/enable the addon) to pick up changes.

2. **Install a local ZIP**
  ```bash
  zip -r plugin.video.sendtokodi-local.zip . -x "*.git*" "__pycache__/*" ".pytest_cache/*"
  ```
  Then in Kodi, use **Install from zip file** and select `plugin.video.sendtokodi-local.zip`.

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

## Development

Run unit tests locally:

```bash
python -m pip install --upgrade pip pytest requests
pytest -q
```

## Code of Conduct
See the [CODE](CODE_OF_CONDUCT.md)

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
