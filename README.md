# SendToKodi (Kodi Add-on)

<p align="center">
  <img src="https://raw.githubusercontent.com/firsttris/chrome.sendtokodi/master/public/banner/1280x800.png" alt="SendToKodi Banner" />
</p>

<p align="center">
  <a href="https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-master.yml"><img src="https://github.com/firsttris/plugin.video.sendtokodi/actions/workflows/build-master.yml/badge.svg" alt="Build" /></a>
  <a href="https://app.codecov.io/gh/firsttris/plugin.video.sendtokodi"><img src="https://codecov.io/gh/firsttris/plugin.video.sendtokodi/graph/badge.svg" alt="Coverage" /></a>
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

## ✅ Requirements

- Kodi 19+
- `script.module.inputstreamhelper` (required for adaptive playback checks)
- `script.module.requests`

Dependencies are installed automatically by Kodi when installing the add-on.

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

## ⚙️ Settings

<details>
  <summary><strong>Settings Details (click to expand)</strong></summary>

Open in Kodi via:

**Add-ons → My add-ons → Video add-ons → SendToKodi → Configure**

### General

- **Enable legacy Python embed workarounds (advanced)**  
  Compatibility toggle for older/edge Python embedding behavior. Keep disabled unless you are troubleshooting runtime issues.
- **Auto-download resolved media before playback**  
  Downloads media to disk first instead of immediate streaming playback.
- **Media download path**  
  Folder used for auto-downloaded files. Default:
  `special://profile/addon_data/plugin.video.sendtokodi/downloads`

### JavaScript Runtime

- **JavaScript runtime mode (auto|deno|quickjs)**  
  Select how JavaScript extraction/runtime tasks are handled:
  - `auto`: prefer best available runtime automatically
  - `deno`: force Deno
  - `quickjs`: force QuickJS
  - `disabled`: disable JavaScript runtime usage
- **QuickJS binary path**  
  Path to your QuickJS executable if you use QuickJS mode.
- **Auto-update Deno JavaScript runtime**  
  Automatically keeps the managed Deno runtime current.
- **Installed Deno version**  
  Read-only display of currently installed Deno.
- **Manage Deno version / Update Deno now**  
  Manual version selection and immediate update actions.
- **Deno version override (advanced)**  
  Pin/override Deno version manually (for advanced troubleshooting).

### yt-dlp

- **Auto-update yt-dlp**  
  Keeps yt-dlp updated automatically (recommended).
- **Installed yt-dlp version**  
  Read-only display of installed yt-dlp.
- **Manage yt-dlp version / Update yt-dlp now**  
  Manually select a version or trigger an immediate update.
- **Additional yt-dlp options (JSON)**  
  Global yt-dlp options as a JSON object, applied to every request. Example:
  `{"cookiefile":"/storage/.kodi/userdata/cookies.txt","format":"best"}`
- **Load additional yt-dlp options from JSON file**  
  Enables loading global yt-dlp options from a JSON file.
- **Additional yt-dlp options file path**  
  Path to a JSON file containing a single JSON object with yt-dlp options.
- **yt-dlp version override (advanced)**  
  Pin/override yt-dlp version manually.

Option precedence for yt-dlp params is:
1. built-in defaults
2. additional options file
3. additional options JSON (settings field)
4. per-request options (`yt-dlp-options` or legacy `ydlOpts`)
5. runtime-specific overrides (e.g. JS runtime options)

### Adaptive

- **Check if my kodi supports adaptive streaming**  
  Runs InputStream Adaptive capability check.
- **Use original manifest (experimental)**  
  Uses the source manifest path instead of generated alternatives.
- **Use DASH manifest builder (kodi 19+ only) (experimental)**  
  Enables internal DASH MPD builder for compatible playback flows.
- **DASH MPD server idle timeout (seconds)**  
  Refresh interval for the generated DASH manifest: after this many idle seconds, the next manifest request triggers a regeneration.
- **Ask which stream to play**  
  Prompts for stream selection when multiple variants are available.
- **Audio-only HLS: disable Opus for native m3u streams**  
  Improves compatibility for some native audio-only HLS playback cases.
- **Maximum resolution**  
  Caps playback stream width (or set Adaptive for automatic quality).

</details>

## 🔌 Integration

- Supported sites: [yt-dlp supported websites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- Call from playlists: [playlist-example.m3u](./playlist-example.m3u)
- Send URLs via JSON-RPC: [Example JSON-RPC request](#example-json-rpc-request)
- Call from another Kodi plugin: [Plugin call example](#call-sendtokodi-from-another-kodi-plugin)
- Add item to Kodi queue: [Queue integration example](#add-item-to-kodi-queue)

<details>
  <summary><strong>Developer Integration Examples (click to expand)</strong></summary>

### Example JSON-RPC request

```json
{
  "jsonrpc": "2.0",
  "method": "Player.Open",
  "params": {
    "item": {
      "file": "plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fsoundcloud.com%2Fspinnin-deep%2Fsam-feldt-show-me-love-edxs-indian-summer-remix-available-june-1"
    }
  },
  "id": 1
}
```

### Example JSON-RPC request with yt-dlp authentication

```json
{
  "jsonrpc": "2.0",
  "method": "Player.Open",
  "params": {
    "item": {
      "file": "plugin://plugin.video.sendtokodi/?url=https%3A%2F%2Fvk.com%2Fvideo-124136901_456239025&yt-dlp-options=%7B%22username%22%3A%22user%40email.com%22%2C%22password%22%3A%22password%20with%20spaces%22%7D"
    }
  },
  "id": 1
}
```

`yt-dlp-options` is passed directly to yt-dlp as a JSON object, so you can provide any supported [yt-dlp options](https://github.com/yt-dlp/yt-dlp#usage-and-options).
For backward compatibility, the legacy `ydlOpts` option key is still supported.

### Call SendToKodi from another Kodi plugin

```python
# Preferred (explicit query param, URL-encoded):
xbmc.executebuiltin("ActivateWindow(10025,'plugin://plugin.video.sendtokodi/?url=<urlencoded_stream_or_playlist_url>',return)")

# Legacy format (still supported):
xbmc.executebuiltin("ActivateWindow(10025,'plugin://plugin.video.sendtokodi/?<stream_or_playlist_url>',return)")
```

### Add item to Kodi queue

```python
# Adds a playable item to Kodi's video playlist without starting playback immediately.
xbmc.executebuiltin("RunPlugin(plugin://plugin.video.sendtokodi/?action=queue&url=<urlencoded_stream_url>&title=<urlencoded_title>)")
```

### Test with Postman

- Create a new HTTP `POST` request.
- Use your Kodi endpoint, e.g. `http://kodi:kodi@192.168.0.138:8080/jsonrpc`.
- Set body type to raw `application/json`.
- Paste one of the JSON-RPC examples and send.

Note: in plugin URLs, query values must be URL-encoded (for example `url=...` and optional `title=...`).

</details>

## 💻 Development

<details>
  <summary><strong>Development Setup (click to expand)</strong></summary>

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

</details>

## 🧰 Troubleshooting

- Stream does not play:
  verify the URL works with yt-dlp and confirm the site is supported.
- Adaptive playback issues:
  run **Check if my Kodi supports adaptive streaming** in Settings → Adaptive.
- Runtime/extractor issues:
  update Deno and yt-dlp from Settings (**Update ... now** actions).
- QuickJS mode does not work:
  check that **QuickJS binary path** points to an existing executable.

Useful checks outside Kodi:

```bash
# Verify a URL can be resolved/playlisted by yt-dlp
yt-dlp --simulate "<url>"

# Show final direct media URL selected by yt-dlp
yt-dlp -g "<url>"
```

## 🤝 Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

This project is licensed under MIT. See [LICENSE.md](LICENSE.md).
