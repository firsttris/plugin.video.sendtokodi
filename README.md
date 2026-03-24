# SendToKodi (Kodi Add-on)

<p align="center">
  <img src="https://raw.githubusercontent.com/firsttris/chrome.sendtokodi/master/public/banner/1280x800.png" alt="SendToKodi Banner" />
</p>

<p align="center">
  <a href="https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml"><img src="https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-publish.yml/badge.svg" alt="Build" /></a>
  <a href="https://kodi.tv"><img src="https://img.shields.io/badge/Kodi-19%2B-17B2E7" alt="Kodi 19+" /></a>
  <a href="https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf"><img src="https://img.shields.io/chrome-web-store/v/gbcpfpcacakaadapjcdchbdmdnfbnbaf?label=Chrome%20Extension" alt="Chrome Extension" /></a>
  <a href="https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf"><img src="https://img.shields.io/chrome-web-store/users/gbcpfpcacakaadapjcdchbdmdnfbnbaf?label=Chrome%20Users" alt="Chrome Users" /></a>
  <a href="https://addons.mozilla.org/firefox/addon/sendtokodi/"><img src="https://img.shields.io/amo/v/sendtokodi?label=Firefox%20Add-on" alt="Firefox Add-on" /></a>
  <a href="https://addons.mozilla.org/firefox/addon/sendtokodi/"><img src="https://img.shields.io/amo/users/sendtokodi?label=Firefox%20Users" alt="Firefox Users" /></a>
</p>

Send video or audio links from your browser or phone directly to [Kodi](https://kodi.tv).
SendToKodi resolves supported websites to playable streams using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## ✨ Features

- 🎬 Stream links from supported websites directly in Kodi
- 🌐 Works with browser extensions and mobile share flows
- 📋 Playlist support via `.m3u`
- 🔧 JSON-RPC and plugin integration support
- 💾 Optional auto-download before playback

## 🚀 Quick Start

1. Install the SendToKodi Kodi add-on (steps below).
2. Install one of the companion apps/extensions.
3. Share or send a video URL to Kodi and start playback.

## 📦 Install in Kodi

This add-on is not in the official Kodi add-on repository.
For automatic updates, first add the SendToKodi repo:

1. Download repository ZIP for Kodi 19+:
   - [repository.sendtokodi-1.0.0.zip](https://github.com/firsttris/repository.sendtokodi/raw/refs/heads/master/repository.sendtokodi-1.0.0.zip)
2. In Kodi, go to **Add-ons → Install from zip file** and install the ZIP.
3. Then go to **Add-ons → Install from repository** and install `plugin.video.sendtokodi`.

Reference: [Kodi Add-on Manager](https://kodi.wiki/view/Add-on_manager)

## 📱 Companion Apps

### Browser extensions

- [Chrome Web Store](https://chrome.google.com/webstore/detail/sendtokodi/gbcpfpcacakaadapjcdchbdmdnfbnbaf)
- [Mozilla Add-ons](https://addons.mozilla.org/firefox/addon/sendtokodi/)
- [Microsoft Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/sendtokodi/cfaaejdnkempodfadjkjfblimmakeaij)

Extension source & issues: [firsttris/chrome.sendtokodi](https://github.com/firsttris/chrome.sendtokodi)

### Mobile

- [Kore (official Kodi Android remote)](https://play.google.com/store/apps/details?id=org.xbmc.kore&hl=de&gl=US)
  - If prompted, set SendToKodi as the preferred add-on in Kore settings.
- The official iOS SendToKodi app is currently retired.
- [Apple Shortcut (iOS + macOS)](https://raw.githubusercontent.com/firsttris/plugin.video.sendtokodi/refs/heads/master/SendToKodi-OSX.shortcut)

## ⚙️ Usage Notes

### Optional: auto-download before playback

In add-on settings (**General**), enable:

`Auto-download resolved media before playback`

Default path:

`special://profile/addon_data/plugin.video.sendtokodi/downloads`

You can change it with:

`Media download path`

## 🔌 Integration

- Supported sites: [yt-dlp supported websites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- Call from playlists: [playlist-example.m3u](./playlist-example.m3u)
- Send URLs via JSON-RPC: [Development docs](./docs/DEVELOPMENT.md#Example-JSON-Request)
- Call from another Kodi plugin: [Development docs](./docs/DEVELOPMENT.md#Call-SendToKodi-Plugin-from-Kodi)

## 💻 Development

Run unit tests locally (recommended: inside a virtual environment):

1. Install venv support (Ubuntu/Debian):

```bash
sudo apt install python3-venv
```

2. Create a virtual environment in the project root:

```bash
python3 -m venv .venv
```

3. Activate it (choose your shell):

- fish:

  ```bash
  source .venv/bin/activate.fish
  ```

- bash/zsh:

  ```bash
  source .venv/bin/activate
  ```

4. Install test dependencies and run tests:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
pytest
```

Coverage reports are generated automatically:

- Console report with missing lines
- `coverage.xml` for CI integrations
- `htmlcov/index.html` as a human-readable report

### Local add-on installation for development

1. **Symlink (recommended)**

```bash
# Standard Kodi install
rm -rf ~/.kodi/addons/plugin.video.sendtokodi
ln -s /home/tristan/Projects/plugin.video.sendtokodi ~/.kodi/addons/plugin.video.sendtokodi

# Flatpak Kodi install
rm -rf /home/tristan/.var/app/tv.kodi.Kodi/data/addons/plugin.video.sendtokodi
ln -s /home/tristan/Projects/plugin.video.sendtokodi /home/tristan/.var/app/tv.kodi.Kodi/data/addons/plugin.video.sendtokodi
```

Restart Kodi (or disable/enable the add-on) after changes.

2. **Install local ZIP**

```bash
zip -r plugin.video.sendtokodi-local.zip . -x "*.git*" "__pycache__/*" ".pytest_cache/*"
```

Then install via **Add-ons → Install from zip file**.

## 🤝 Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

This project is licensed under MIT. See [LICENSE.md](LICENSE.md).
