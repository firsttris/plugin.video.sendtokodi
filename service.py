# -*- coding: utf-8 -*-
import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import YDStreamExtractor

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
strparams = str(params)
vid = YDStreamExtractor.getVideoInfo(strparams)
title = vid.selectedStream()['title']
thumbnail = vid.selectedStream()['thumbnail']
stream_url = vid.streamURL()
play_item = xbmcgui.ListItem(title, path=stream_url)
play_item.setInfo(type='Video', infoLabels={'Title':title})
play_item.setArt({'thumb': thumbnail})
# xbmc.Player().play(stream_url, play_item)
# Pass the item to the Kodi player.
showInfoNotification("Playing... " +title)
xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)