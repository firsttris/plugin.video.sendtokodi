# -*- coding: utf-8 -*-
import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from youtube_dl import YoutubeDL

class replacement_stderr(sys.stderr.__class__):
    def isatty(self): return False

sys.stderr.__class__ = replacement_stderr

# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])

def debug(content):
    log(content, xbmc.LOGDEBUG)

def notice(content):
    log(content, xbmc.LOGNOTICE)

def log(msg, level=xbmc.LOGNOTICE):
    addon = xbmcaddon.Addon()
    addonID = addon.getAddonInfo('id')
    xbmc.log('%s: %s' % (addonID, msg), level)

def showInfoNotification(message):
    xbmcgui.Dialog().notification("SendToKodi", message, xbmcgui.NOTIFICATION_INFO, 5000)

def showErrorNotification(message):
    xbmcgui.Dialog().notification("SendToKodi", message, xbmcgui.NOTIFICATION_ERROR, 5000)

def getParams():
    paramstring = sys.argv[2]
    cleanedparams = paramstring[1:]
    return cleanedparams

params = getParams()
url = str(params)
ydl = YoutubeDL()
ydl.add_default_info_extractors()


with ydl:
    result = ydl.extract_info(url, download=False)
if 'entries' in result:
    # Can be a playlist or a list of videos
    pl = xbmc.PlayList(1)
    pl.clear()
    for video in result['entries']:
        debug('Video #%d: %s' % (video['playlist_index'], video['title']))
        url = video['formats'][-1]['url']
        thumbnail = video['thumbnail']
        title = video['title']
        play_item = xbmcgui.ListItem(title, path=url)
        play_item.setInfo(type='Video', infoLabels={'Title': title})
        play_item.setArt({'thumb': thumbnail})
        xbmc.PlayList(1).add(url, play_item)
    xbmc.Player().play(pl)
else:
    # Just a video
    debug(result)
    title = result['title']
    debug("Title: " + title)
    thumbnail = result['thumbnail']
    debug("Thumbnail: " + thumbnail)
    url = result['formats'][-1]['url']
    debug("Url: " + url)
    play_item = xbmcgui.ListItem(title, path=url)
    play_item.setInfo(type='Video', infoLabels={'Title': title})
    play_item.setArt({'thumb': thumbnail})
    # Pass the item to the Kodi player.
    showInfoNotification("Playing... " + title)
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)