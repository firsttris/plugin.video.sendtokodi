---
description: Develop the SendToKodi Kodi add-on. Local setup, running the unit tests with pytest and coverage, the project structure, running the add-on from a checkout in Kodi, continuous integration, releases and the SendToKodi repository, writing documentation.
---

# Development

The add-on is plain Python 3 on top of Kodi's `xbmc*` modules. The logic lives in the `core` package and is unit-tested
without Kodi; `service.py` is the thin entry point Kodi runs.

## Setup

Requirements: Python 3.8 or newer (Kodi 19 ships Python 3.8, newer Kodi releases newer versions; CI tests with 3.12)
and `pip`.

```bash
git clone https://github.com/firsttris/plugin.video.sendtokodi.git
cd plugin.video.sendtokodi
python3 -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

On Debian and Ubuntu, `python3-venv` has to be installed first (`sudo apt install python3-venv`).

## Tests

```bash
pytest
```

`pytest.ini` turns on coverage for every run. You get a console report with the missing lines, `coverage.xml` for CI
and `htmlcov/index.html` to browse. `tests/conftest.py` provides stand-ins for the `xbmc`, `xbmcaddon`, `xbmcgui`,
`xbmcplugin` and `xbmcvfs` modules, so the tests run on a normal Python. The tests cover parameter parsing, stream
selection, the DASH builder, the runtime managers with their update policy, subtitles and the runtime actions.

Add a test for every change in `core`; CI refuses pull requests whose tests fail, and the coverage is reported to
[Codecov](https://app.codecov.io/gh/firsttris/plugin.video.sendtokodi).

## Project structure

| Path | Contents |
|---|---|
| `service.py` | Entry point. Parses the request, prepares yt-dlp, resolves, hands the result to Kodi. Everything Kodi-specific that is hard to test lives here. |
| `addon.xml` | Add-on manifest: ID, dependencies, metadata. The version is written in by the release build. |
| `resources/settings.xml` | The settings dialog. Labels are string IDs from `resources/language/resource.language.en_gb/strings.po`. |
| `core/addon_params.py` | Parsing of the plugin URL (`url`, `yt-dlp-options`, `action=queue`, the legacy form), the yt-dlp option merge, the JavaScript runtime choice, reading the settings. |
| `core/playback_selection.py` | Chooses the stream to play from yt-dlp's formats: manifest, DASH builder or progressive, resolution cap, headers. |
| `core/dash_builder.py` | Builds DASH manifests from separate video and audio formats and serves them from a local HTTP server. |
| `core/runtime/playback.py` | Turns a yt-dlp result into Kodi `ListItem`s: single videos, playlists, subtitles, InputStream Adaptive properties. |
| `core/runtime/actions.py` | The settings actions: update now, manage versions, preparing the managed yt-dlp before a playback and the runtime update check after it. |
| `core/managed_runtime.py` | Shared logic of the managed runtimes: version folders, pruning, update state. |
| `core/ytdlp_manager.py`, `core/deno_manager.py` | Download, install, activate and list yt-dlp and Deno versions. |
| `core/update_policy.py`, `core/runtime_update_state.py` | Check intervals, backoff and the persisted update state. |
| `core/subtitle_support.py` | Safe file names for downloaded subtitles. |
| `core/service_runtime.py` | Workarounds for Kodi's embedded Python (`strptime`, `stderr`). |
| `tests/` | pytest suite, one file per module. |
| `docs/`, `mkdocs.yml` | This documentation. |
| `.github/` | Workflows and the build and publish scripts. |

## Running the add-on from a checkout

Kodi loads add-ons from its `addons` folder, so the simplest way is a symlink to the checkout:

```bash
# Standard Kodi installation
rm -rf ~/.kodi/addons/plugin.video.sendtokodi
ln -s ~/Projects/plugin.video.sendtokodi ~/.kodi/addons/plugin.video.sendtokodi

# Flatpak Kodi
rm -rf ~/.var/app/tv.kodi.Kodi/data/addons/plugin.video.sendtokodi
ln -s ~/Projects/plugin.video.sendtokodi ~/.var/app/tv.kodi.Kodi/data/addons/plugin.video.sendtokodi
```

Enable the add-on in Kodi once (*Add-ons → My add-ons → Video add-ons → SendToKodi*). The dependencies have to be
installed; installing a release first and then replacing the folder with the symlink is the easiest way to get them.
After a code change, restart Kodi or disable and re-enable the add-on; Kodi caches nothing between playbacks, but the
settings dialog is read on start.

Alternatively, build a ZIP and install it with *Install from zip file*:

```bash
zip -r plugin.video.sendtokodi-local.zip . -x "*.git*" "__pycache__/*" ".pytest_cache/*" ".venv/*" "site/*"
```

Kodi's log (`kodi.log` in the user data folder) is where `log()` calls from the add-on end up; `kodi -d` on Linux or
*Settings → System → Logging → Enable debug logging* raises the level.

## Continuous integration

- **build-pr** runs the tests and builds the add-on ZIP for every pull request against `master`; the ZIP is attached
  to the run as an artifact for manual testing. Draft pull requests don't build; marking them *Ready for review* does.
- **build-master** runs the tests on every push to `master` and uploads the coverage to Codecov.
- **Docs** builds this documentation with `mkdocs build --strict` for pull requests that touch `docs/` and publishes
  it to GitHub Pages on `master`.

Documentation-only changes (`*.md`, `docs/`) don't trigger the test builds.

## Releases

A release is a tag `vX.Y.Z`, the same scheme as in [firsttris/workflows](https://github.com/firsttris/workflows):

1. *Actions → Bump version → Run workflow* with `patch`, `minor` or `major`. The workflow raises the highest existing
   tag, tags the current commit on `master` and starts the release.
2. **Release** runs the tests, builds the add-on ZIP with the version from the tag written into `addon.xml`
   (`.github/scripts/build-addon.sh`), publishes it to the Kodi repository
   [firsttris/repository.sendtokodi](https://github.com/firsttris/repository.sendtokodi)
   (`.github/scripts/publish-addon.sh`, which adds the ZIP, updates the repository's `addon.xml` with the new version
   and writes its MD5 file) and creates a GitHub release with generated notes and the ZIP.
3. Kodi installations with the SendToKodi repository pick up the new version at their next add-on update check.

`addon.xml` in the repository keeps a placeholder version; the build scripts set the real one. Nothing has to be
edited by hand for a release.

## Writing documentation

The documentation is Markdown in `docs/`, built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
and published at [firsttris.github.io/plugin.video.sendtokodi](https://firsttris.github.io/plugin.video.sendtokodi/).

```bash
pip install -r requirements-docs.txt
mkdocs serve        # live preview at http://127.0.0.1:8000
mkdocs build --strict
```

`mkdocs.yml` holds the navigation; add new pages there. Every page starts with a `description` in its front matter,
which becomes the page's meta description for search engines. Links between pages are relative Markdown links
(`settings.md#yt-dlp`), which work on GitHub and on the site alike. `--strict` fails on broken links, so run it before
pushing; CI runs it on every pull request. The README on GitHub stays the short overview and links here for details.
