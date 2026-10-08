# Code-Review plugin.video.sendtokodi

Stand: 2026-10-08, Commit `d138832` (master)

Gesamteindruck: Das Projekt ist in gutem Zustand. Reine Logik liegt in `core/`, Kodi-spezifischer Glue in
`service.py` und `core/runtime/`. 353 Tests laufen grün, der Netzwerkzugriff ist in den Tests geblockt.
Echte Fehler gibt es wenige, dafür einige klare Beschleuniger.

## 1. Fehler und Risiken

### 1.1 Deno auf Android wird falsch erkannt

`core/deno_manager.py:48` (`_PLATFORM_MAP`) und `_detect_platform()`.

Auf Android meldet Python `platform.system() == "Linux"` und `platform.machine() == "aarch64"`. Der Manager
lädt deshalb den glibc-Build `deno-aarch64-unknown-linux-gnu.zip` (~40 MB), der auf Android (Bionic libc,
häufig `noexec` auf dem Datenverzeichnis) nicht läuft. Danach schlägt jede YouTube-Extraktion leise fehl.

Vorschlag: Android erkennen und Deno überspringen, stattdessen QuickJS vorschlagen.

```python
def _is_android():
    if hasattr(sys, "getandroidapilevel"):
        return True
    try:
        import xbmc
        return xbmc.getCondVisibility("System.Platform.Android")
    except ImportError:
        return False
```

### 1.2 `patch_strptime` ist nicht idempotent

`core/service_runtime.py:16`

Jeder Aufruf setzt eine neue Subklasse der vorherigen Subklasse auf `datetime.datetime`. Heute harmlos,
weil pro Aufruf ein frischer Interpreter läuft. Sobald `reuselanguageinvoker` aktiviert wird (siehe 2.1),
wächst die Vererbungskette bei jedem Playback.

Vorschlag: Guard-Attribut setzen und beim zweiten Aufruf nichts tun.

### 1.3 `maxresolution` wird ohne Schutz geparst

`service.py:220`

```python
maxresolution_setting = int(xbmcplugin.getSetting(__handle__, "maxresolution"))
```

Bei leerem oder ungültigem Wert fliegt ein unbehandelter `ValueError`. Alle anderen Settings werden
defensiv gelesen (siehe `resolve_dash_httpd_idle_timeout`). Gleiche Behandlung hier.

### 1.4 Update-Check blockiert den Playback-Pfad

`core/runtime/actions.py` (`configure_managed_ytdlp`) und `core/deno_manager.py` (`get_ydl_opts`).

Bei abgelaufenem Cache (alle 6 h) wird synchron die GitHub-API abgefragt (Timeout 20 s), bei neuer Version
heruntergeladen und entpackt. Das passiert, bevor die URL überhaupt aufgelöst wird. Ein Abspielen kann also
20 s und länger hängen, bevor etwas passiert.

Vorschlag: Installierte Version sofort nutzen. Den Update-Check in einem Thread nach `setResolvedUrl`
laufen lassen oder in ein Kodi-Service-Addon (`xbmc.python.service`) auslagern.

### 1.5 Downloads landen komplett im RAM

`core/managed_runtime.py` (`download_with_progress`).

Die Datei wird in `chunks` gesammelt und mit `b"".join()` zurückgegeben. Beim Deno-Zip sind das ~40 MB
plus Kopie beim Entpacken. Auf einem Raspberry Pi oder Fire-TV-Stick ist das relevant.

Vorschlag: In eine Temp-Datei streamen und `zipfile`/`tarfile` auf die Datei öffnen.

### 1.6 Settings-Leiche `deno_enabled`

`core/addon_params.py:259` (`resolve_deno_settings`) liest `deno_enabled`. Das Setting existiert in
`resources/settings.xml` nicht mehr. Der Wert ist immer `False` und wird nirgends ausgewertet.

## 2. Schneller

### 2.1 `reuselanguageinvoker` aktivieren

`addon.xml`

```xml
<extension point="xbmc.python.pluginsource" library="service.py">
    <provides>video</provides>
    <reuselanguageinvoker>true</reuselanguageinvoker>
</extension>
```

Kodi behält dann den Python-Interpreter samt importiertem `yt_dlp` und `requests` zwischen den Aufrufen.
Das ist der größte Hebel für die Startzeit. Nebeneffekt: Der DASH-HTTP-Server in `dash_builder` überlebt
dann zuverlässig, weil der Interpreter nicht abgeräumt wird.

Voraussetzungen:

- Idempotenz-Fix für `patch_strptime` (1.2).
- `install_stderr_workaround` ebenfalls nur einmal ausführen.
- Ein Versionswechsel von yt-dlp greift erst nach Kodi-Neustart, weil `yt_dlp` in `sys.modules` bleibt.
  Alternativ nach `activate_runtime` alle `yt_dlp*`-Einträge aus `sys.modules` entfernen.
- Modul-Globals wie `_isa_support_cache` bleiben erhalten (hier erwünscht).

### 2.2 Lazy Extractors nach der Installation erzeugen

`core/ytdlp_manager.py` (`_download_and_install`).

Das Tag-Tarball von GitHub enthält kein `yt_dlp/extractor/lazy_extractors.py`. Ohne diese Datei importiert
jeder Aufruf alle ~1800 Extractor-Module. Das Script `devscripts/make_lazy_extractors.py` liegt im Tarball
und kann einmal nach dem Entpacken laufen.

Messung auf x86 (`import yt_dlp` + `YoutubeDL()`):

| | kalter Bytecode-Cache | warmer Cache |
|---|---|---|
| ohne lazy_extractors | 1,8 s | 0,45 s |
| mit lazy_extractors | 0,5 s | 0,23 s |

Auf ARM-Geräten ist das Mehrfache davon zu erwarten.

Hinweis: Das Tarball muss dann auch `devscripts/` enthalten, aktuell wird nur `yt_dlp/` extrahiert.
Alternativ das Script einmalig mit ins Addon packen.

### 2.3 Untertitel parallel laden

`core/runtime/playback.py:64` (`_resolve_subtitle_paths`).

Pro Sprache ein sequenzieller Request mit 20 s Timeout, alles vor dem Playback. Bei vielen Sprachen
summiert sich das. Wie bei `Manifest.prefetch_ranges` einen `ThreadPoolExecutor` nutzen.

### 2.4 Range-Probe lädt den Prefix mehrfach

`core/dash_builder.py` (`find_init_and_index_ranges`).

Die Probe holt 4 KB, dann 16 KB ab Byte 0, dann 64 KB ab Byte 0, dann 256 KB ab Byte 0. Besser nur den
fehlenden Bereich (`bytes=4096-16383`) nachladen und an den Puffer anhängen.

### 2.5 Optionsparser zweimal pro Aufruf

`core/addon_params.py` (`load_ytdlp_config_options`).

`parse_options(['--ignore-config'])` und `parse_options([... '--config-locations', ...])` bauen beide den
kompletten yt-dlp-Optionsparser. Die Defaults ändern sich nur mit der yt-dlp-Version und könnten gecacht
werden.

### 2.6 Kleinkram

- `log()` in `service.py` erzeugt pro Logzeile ein `xbmcaddon.Addon()`. Addon-ID einmal auf Modulebene lesen.
- `refresh_runtime_displays` beim Öffnen der Settings ruft für yt-dlp `get_runtime_status`, das immer GitHub
  fragt (siehe 3.3). Das Öffnen der Settings kann dadurch am Netz hängen.

## 3. Besser

### 3.1 Release-Zip enthält Tests und Doku

`.github/scripts/build-addon.sh`

Der Ausschluss ist nur `-x "*.git*"`. Dadurch landen `tests/` (772 KB) und `docs/` (588 KB) sowie
`mkdocs.yml`, `.coveragerc`, `pytest.ini`, `requirements*.txt` im Zip, das an Nutzer ausgeliefert wird.

```bash
zip -r "$RUNNER_TEMP/plugin.video.sendtokodi-$VERSION.zip" plugin.video.sendtokodi \
    -x "*.git*" "*/tests/*" "*/docs/*" "*/mkdocs.yml" "*/.coveragerc" "*/pytest.ini" \
       "*/requirements*.txt" "*/.editorconfig" "*/CODE_REVIEW.md"
```

### 3.2 Eine Konstante mit zwei Bedeutungen

`core/dash_builder.py` (`DASH_HTTPD_IDLE_TIMEOUT_SECONDS`).

Die Konstante steuert sowohl das Abschalten des HTTP-Servers bei Inaktivität als auch, wann ein Manifest
per `resolve_fresh_result` neu aufgelöst wird. Zwei Konstanten (Idle-Timeout, Manifest-TTL) machen das
Setting `dash_httpd_idle_timeout` verständlicher.

### 3.3 `get_runtime_status` ist uneinheitlich

`core/deno_manager.py` hat `include_latest=False` als Default, `core/ytdlp_manager.py` fragt immer die
GitHub-API. Gleiche Signatur für beide, Netz nur auf Anforderung.

### 3.4 `select_playback_source` ist sehr lang

`core/playback_selection.py:620` bis `:845`, 225 Zeilen mit tiefer Verschachtelung. Die Tests decken es gut
ab, aber eine Aufteilung in „Kandidaten sammeln“ (Original-Manifest, Format-Manifest, DASH-Builder, Raw,
Fallbacks) und „Kandidaten priorisieren“ würde die Reihenfolge der Entscheidungen sichtbar machen.

### 3.5 Weitere Punkte

- `requests` und `urllib.request` werden gemischt verwendet (`dash_builder`, `playback` vs. `managed_runtime`).
  Eine Bibliothek reicht.
- `exit()` in `service.py` ist das `site`-Builtin; `sys.exit()` ist die saubere Variante.
- `pytest.ini` schaltet Coverage bei jedem lokalen Testlauf ein. Das bremst den Entwicklungszyklus; Coverage
  nur in CI (`pytest --cov` im Workflow) aktivieren.
- `play_playlist_result`: `extract_starting_entry(url, download=False)` ignoriert den Parameter und nutzt
  `media_download_enabled`. Funktioniert, ist aber irreführend. Außerdem fehlt hier der Fortschrittsdialog,
  den der Einzelvideo-Pfad über `download_result_with_progress` zeigt.
- `_prompt_preferred_stream_url` gibt ein Dict zurück, der Name suggeriert eine URL.

## 4. Empfohlene Reihenfolge

Bestes Verhältnis von Aufwand zu Wirkung:

1. Android-Erkennung für Deno (1.1)
2. `reuselanguageinvoker` mit den Idempotenz-Fixes (2.1, 1.2)
3. Lazy Extractors nach der Installation (2.2)
4. Zip-Ausschlüsse im Build (3.1)
5. Update-Check aus dem Playback-Pfad nehmen (1.4)
6. Untertitel parallel, Range-Probe inkrementell (2.3, 2.4)
