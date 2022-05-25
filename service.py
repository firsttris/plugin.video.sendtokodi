# -*- coding: utf-8 -*-
import json
import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

class replacement_stderr(sys.stderr.__class__):
    def isatty(self): return False

sys.stderr.__class__ = replacement_stderr

def debug(content):
    log(content, xbmc.LOGDEBUG)


def notice(content):
    log(content, xbmc.LOGINFO)


def log(msg, level=xbmc.LOGINFO):
    addon = xbmcaddon.Addon()
    addonID = addon.getAddonInfo('id')
    xbmc.log('%s: %s' % (addonID, msg), level)


# python embedded (as used in kodi) has a known bug for second calls of strptime. 
# The python bug is docmumented here https://bugs.python.org/issue27400 
# The following workaround patch is borrowed from https://forum.kodi.tv/showthread.php?tid=112916&pid=2914578#pid2914578
def patch_strptime():
    import datetime

    #fix for datatetime.strptime returns None
    class proxydt(datetime.datetime):
        @staticmethod
        def strptime(date_string, format):
            import time
            return datetime.datetime(*(time.strptime(date_string, format)[0:6]))

    datetime.datetime = proxydt


def showInfoNotification(message):
    xbmcgui.Dialog().notification("SendToKodi", message, xbmcgui.NOTIFICATION_INFO, 5000)


def showErrorNotification(message):
    xbmcgui.Dialog().notification("SendToKodi", message,
                                  xbmcgui.NOTIFICATION_ERROR, 5000)


# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])


def getParams():
    result = {}
    paramstring = sys.argv[2]
    additionalParamsIndex = paramstring.find(' ')
    if additionalParamsIndex == -1:
        result['url'] = paramstring[1:]
        result['ydlOpts'] = {}
    else:
        result['url'] = paramstring[1:additionalParamsIndex]
        additionalParamsString = paramstring[additionalParamsIndex:]
        additionalParams = json.loads(additionalParamsString)
        result['ydlOpts'] = additionalParams['ydlOpts']
    return result


def createListItemFromVideo(video):
    debug(video)
    url = video['url']
    thumbnail = video.get('thumbnail')
    title = video['title']
    list_item = xbmcgui.ListItem(title, path=url)
    list_item.setInfo(type='Video', infoLabels={'Title': title})

    if thumbnail is not None:
        list_item.setArt({'thumb': thumbnail})

    return list_item

def createListItemFromFlatPlaylistItem(video):
    listItemUrl = __url__ + "?" + video['url']
    title = video['title']

    # add the extra parameters to every playlist item
    paramstring = sys.argv[2]
    additionalParamsIndex = paramstring.find(' ')
    if additionalParamsIndex != -1:
        additionalParamsString = paramstring[additionalParamsIndex:]
        listItemUrl = listItemUrl + " " + additionalParamsString
    
    listItem = xbmcgui.ListItem(
        path            = listItemUrl,
        label           = title
    )

    # the method isn't available in Kodi < 18. Doesn't seem to affect behavior, and can probably be set manually using setProperty() if needed
    # listItem.setIsFolder(False)

    listItem.setInfo(
        type        = 'Video', # not really known at this point, but required
        infoLabels  = {'Title': title }
    )

    # both `true` and `false` are recommended here...
    listItem.setProperty("IsPlayable","true")

    return listItem


# Use the chosen resolver while forcing to use youtube_dl on legacy python 2 systems (dlp is python 3.6+)
if xbmcplugin.getSetting(int(sys.argv[1]),"resolver") == "0" or sys.version_info[0] == 2:
    from lib.youtube_dl import YoutubeDL
else:
    from lib.yt_dlp import YoutubeDL
    
# patch broken strptime (see above)
patch_strptime()


# extract_flat:  Do not resolve URLs, return the immediate result.
#                Pass in 'in_playlist' to only show this behavior for
#                playlist items.
ydl_opts = {
    'format': 'best',
    'extract_flat': 'in_playlist'
}

params = getParams()
url = str(params['url'])
ydl_opts.update(params['ydlOpts'])
ydl = YoutubeDL(ydl_opts)
ydl.add_default_info_extractors()

with ydl:
    showInfoNotification("resolving stream(s) for " + url)
    result = ydl.extract_info(url, download=False)

if 'entries' in result:
    # more than one video
    pl = xbmc.PlayList(1)
    pl.clear()

    # make sure first ListItem has a resolved url, to avoid recursion and Kodi crashes
    firstVideoUrl = result['entries'][0]['url']
    firstItem = createListItemFromVideo(ydl.extract_info(firstVideoUrl, download=False))
    pl.add(firstItem.getPath(), firstItem)
    
    for video in result['entries'][1:]:
        list_item = createListItemFromFlatPlaylistItem(video)
        pl.add(list_item.getPath(), list_item)

    #xbmc.Player().play(pl) # this probably works again
    # ...but start playback the same way the Youtube plugin does it:
    xbmc.executebuiltin('Playlist.PlayOffset(%s,%d)' % ('video', 0))

    showInfoNotification("playing playlist " + result['title'])
else:
    # Just a video, pass the item to the Kodi player.
    showInfoNotification("playing title " + result['title'])
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=createListItemFromVideo(result))
