"""Setting access that also works when the handle has no plugin directory.

Kodi resolves plugin settings through the handle, and only sets one up for a
directory listing. Called from a context menu, the OSD, the service or JSON-RPC,
xbmcplugin.getSetting() returns '' for every id, which silently resets settings
to their defaults -- measured: ytdlp_source came back empty, normalize_source('')
chose 'stable', and a download asked for a managed yt-dlp while playback used
the system one.

Falling back to the add-on's own settings keeps the user's choice. This lives in
its own module so that every caller shares one implementation instead of each
one deciding where to read from.
"""


def get_setting(handle, setting_id):
    # Imported here rather than at module level: this module stays importable
    # without Kodi (tests, tooling), and a test that swaps the Kodi modules sees
    # the current ones instead of the ones present at import time.
    import xbmcaddon
    import xbmcplugin

    value = xbmcplugin.getSetting(handle, setting_id)
    if value:
        return value
    addon_get_setting = getattr(xbmcaddon.Addon(), "getSetting", None)
    if addon_get_setting is None:
        return value
    return addon_get_setting(setting_id) or value
