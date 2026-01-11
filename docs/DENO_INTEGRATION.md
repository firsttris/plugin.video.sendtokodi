# Deno JavaScript Runtime Integration

## Overview

yt-dlp now requires a JavaScript runtime for proper YouTube extraction. Without it, you may experience:
- Only audio being played (no video)
- Infinite loading/spinning wheel
- Failed video extraction

SendToKodi **automatically handles this** by downloading and configuring [Deno](https://deno.land/) on first use.

## Quick Start

**Nothing to do!** Just update SendToKodi and use it normally:
1. Send a YouTube URL to Kodi
2. First time: Deno downloads automatically (~100MB, progress shown)
3. Video plays with full quality

## How It Works

1. **Auto-Detection**: Checks for system-installed Deno first
2. **Auto-Download**: Downloads appropriate binary for your platform if needed
3. **Auto-Configuration**: Configures yt-dlp transparently

## Configuration

In SendToKodi settings under "General":

### Auto-download Deno (JavaScript runtime)
- **Default**: Enabled
- **Purpose**: Automatically downloads Deno binary if not found on system
- When disabled, SendToKodi will only use Deno if it's already installed on your system

### Suppress YouTube JS warning (fallback mode)
- **Default**: Disabled  
- **Purpose**: Uses `player_client=default` to suppress warnings when Deno is not available
- This is a fallback mode that may result in missing formats or degraded functionality
- Only useful if you don't want to use Deno but want to suppress warning messages

## Technical Details

### Binary Storage
Deno binaries are stored in your Kodi addon data directory:
```
special://profile/addon_data/plugin.video.sendtokodi/deno/
```

### Supported Platforms
- Linux (x86_64, aarch64)
- macOS/Darwin (x86_64, aarch64/arm64)
- Windows (x86_64)

### Version
Current Deno version: **v2.6.4** (latest stable, compatible with yt-dlp)

### Size
Deno binary size varies by platform:
- Linux: ~100MB
- macOS: ~100MB  
- Windows: ~100MB

The download happens in the background with a progress indicator.

## Troubleshooting

### Video only plays audio
- Ensure "Auto-download Deno" is enabled in settings
- Check Kodi log for Deno download/configuration messages
- Try clearing the Deno directory and restarting Kodi to force re-download

### Download fails
- Check your internet connection
- Check Kodi log for specific error messages
- Ensure you have sufficient disk space (~150MB free)
- Check that Kodi has write permissions to addon data directory

### Using system Deno
If you have Deno installed system-wide (in PATH), SendToKodi will detect and use it automatically, skipping the download.

## Manual Deno Installation

If you prefer to manage Deno yourself:

1. Install Deno using official method: https://deno.land/manual/getting_started/installation
2. Disable "Auto-download Deno" in SendToKodi settings
3. SendToKodi will detect and use your system Deno

## For Developers

The Deno integration is implemented in `lib/deno_manager.py`. Key functions:

- `ensure_deno_available(auto_download=True)`: Ensures Deno is available
- `get_ydl_deno_config(auto_download=True)`: Returns yt-dlp configuration dict
- `is_deno_available()`: Checks for existing Deno installation

Configuration passed to yt-dlp:
```python
{
    'js_runtimes': {
        'deno': {'location': '/path/to/deno'}
    },
    'remote_components': ['ejs:github']
}
```

### Deno Permissions

Deno has a security-first approach with granular permissions. When yt-dlp invokes Deno for JavaScript extraction, it automatically handles the necessary permissions:

- `--allow-net` - Network access for downloading player code
- `--allow-read` - Reading cached data
- `--allow-write` - Writing to cache
- `--allow-env` - Environment variable access

You don't need to configure these manually - yt-dlp passes the required permissions when executing Deno. The integration is transparent and secure.

## For Developers

### Testing Outside Kodi

```bash
# Test Deno manager
python3 test_deno_manager.py

# Test with real yt-dlp extraction
python3 example_deno_usage.py
```

### Integration Code

The Deno integration is in `lib/deno_manager.py`. Key functions:

```python
# Get yt-dlp configuration (returns dict ready to merge)
from deno_manager import get_ydl_deno_config

deno_config = get_ydl_deno_config(auto_download=True)
if deno_config:
    ydl_opts.update(deno_config)
```

Configuration returned:
```python
{
    'js_runtimes': {'deno': {'location': '/path/to/deno'}},
    'remote_components': ['ejs:github']
}
```

### Platform Support
- Linux (x86_64, aarch64)
- macOS (x86_64, arm64)
- Windows (x86_64)

## References

- [yt-dlp EJS (Embedded JavaScript) documentation](https://github.com/yt-dlp/yt-dlp/wiki/EJS)
- [Deno official website](https://deno.land/)
- [Deno GitHub releases](https://github.com/denoland/deno/releases)
