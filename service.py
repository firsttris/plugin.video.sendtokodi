# -*- coding: utf-8 -*-
import os
import shlex
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from youtube_dl import YoutubeDL


class replacement_stderr(sys.stderr.__class__):
    def isatty(self): return False


sys.stderr.__class__ = replacement_stderr



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
    xbmcgui.Dialog().notification("SendToKodi", message,
                                  xbmcgui.NOTIFICATION_ERROR, 5000)


# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])


def getParams():
    allowedArgs = {
        '--password': 'password',
        '-p': 'password',
        '--username': 'username',
        '-u': 'username',
    }
    paramstring = sys.argv[2]
    additionalArgsIndex = paramstring.find(' ')
    if additionalArgsIndex == -1:
        cleanUrl = paramstring[1:]
        additionalArgsString = ''
    else:
        cleanUrl = paramstring[1:additionalArgsIndex]
        additionalArgsString = paramstring[additionalArgsIndex:]
    additionalArgs = shlex.split(additionalArgsString) # shlex will get --username USERNAME --password "PASS WORD" and return ["--username", "USERNAME", "--password", "PASS WORD"]. if you provide shlex "   "(empty string), shlex will return empty array
    result = {
        'url': cleanUrl
    }
    argName = None
    for arg in additionalArgs:
        if argName is None:
            if arg in allowedArgs:
                argName = allowedArgs[arg]
            else:
                raise ValueError(arg + ' arg is not a valid argument. allowed arguments: [' + ', '.join(allowedArgs.keys()) + ']')
        else:
            result[argName] = arg
            argName = None
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
   

ydl_opts = {
    'format': 'best'
}

params = getParams()
url = str(params['url'])
if 'username' in params:
    ydl_opts['username'] = params['username']
if 'password' in params:
    ydl_opts['password'] = params['password']
ydl = YoutubeDL(ydl_opts)
ydl.add_default_info_extractors()

with ydl:
    showInfoNotification("resolving stream(s) for " + url)
    result = ydl.extract_info(url, download=False)

if 'entries' in result:
    # Playlist
    pl = xbmc.PlayList(1)
    pl.clear()
    for video in result['entries']:
        list_item = createListItemFromVideo(video);
        xbmc.PlayList(1).add(list_item.getPath(), list_item)
    xbmc.Player().play(pl)
    showInfoNotification("playing playlist " + result['title'])
else:
    # Just a video, pass the item to the Kodi player.
    showInfoNotification("playing title " + result['title'])
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=createListItemFromVideo(result))
