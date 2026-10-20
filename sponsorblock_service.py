# -*- coding: utf-8 -*-
"""Background service that skips SponsorBlock segments of YouTube videos played by SendToKodi."""
import xbmc
import xbmcaddon
import xbmcgui

from core import sponsorblock

ADDON_ID = 'plugin.video.sendtokodi'
POLL_INTERVAL_SECONDS = 0.25


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('%s: SponsorBlock: %s' % (ADDON_ID, msg), level)


class SponsorBlockPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.started = False
        self.skipper = None
        self.notify = True

    def onAVStarted(self):
        # Every new item, also the next one of a playlist, is looked at again in the service loop.
        self.started = True
        self.skipper = None

    def onPlayBackStopped(self):
        self.started = False
        self.skipper = None

    onPlayBackEnded = onPlayBackStopped
    onPlayBackError = onPlayBackStopped


def _playing_item_video_id(player):
    try:
        return player.getPlayingItem().getProperty(sponsorblock.VIDEO_ID_PROPERTY)
    except Exception:
        # getPlayingItem() needs Kodi 20.
        return ''


def load_skipper(player):
    """Return a SegmentSkipper for the current playback, or None if there is nothing to skip."""
    settings = sponsorblock.resolve_sponsorblock_settings(xbmcaddon.Addon(ADDON_ID).getSetting)
    if not settings['enabled'] or not player.isPlayingVideo():
        return None
    video_id = sponsorblock.resolve_playing_video_id(
        _playing_item_video_id(player),
        player.getPlayingFile(),
        xbmcgui.Window(10000).getProperty(sponsorblock.PLAYBACK_PROPERTY),
    )
    if video_id is None:
        return None
    try:
        segments = sponsorblock.fetch_skip_segments(video_id, settings['categories'], settings['api_url'])
    except Exception as exc:
        log("Could not fetch segments for {}: {}".format(video_id, exc), xbmc.LOGWARNING)
        return None
    log("{} segments to skip in {}".format(len(segments), video_id))
    player.notify = settings['notify']
    return sponsorblock.SegmentSkipper(segments) if segments else None


def skip_if_needed(player):
    try:
        current_time = player.getTime()
    except RuntimeError:
        # Playback ended between the callback and this check.
        return
    target = player.skipper.seek_target(current_time)
    if target is None:
        return
    log("Skipping from {:.1f}s to {:.1f}s".format(current_time, target))
    player.seekTime(target)
    if player.notify:
        xbmcgui.Dialog().notification(
            "SendToKodi",
            xbmcaddon.Addon(ADDON_ID).getLocalizedString(34020),
            xbmcgui.NOTIFICATION_INFO,
            2000,
        )


def run():
    monitor = xbmc.Monitor()
    player = SponsorBlockPlayer()
    while not monitor.waitForAbort(POLL_INTERVAL_SECONDS):
        try:
            tick(player)
        except Exception as exc:
            # Kodi's player calls fail when playback stops in between; keep the service alive.
            log("Check failed: {}".format(exc), xbmc.LOGWARNING)


def tick(player):
    if player.started:
        player.started = False
        skipper = load_skipper(player)
        # Another item may have started while the segments were fetched; it is loaded next time.
        if player.started:
            return
        player.skipper = skipper
    if player.skipper is not None and player.isPlayingVideo():
        skip_if_needed(player)


if __name__ == '__main__':
    run()
