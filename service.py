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


def extract_manifest_url(result):
    # sometimes there is an url directly 
    # but for some extractors this is only one quality and sometimes not even a real manifest
    if 'manifest_url' in result and get_adaptive_type_from_url(result['manifest_url']):
        return result['manifest_url']
    # otherwise we must relay that the requested formats have been found and 
    # extract the manifest url from them
    if 'requested_formats' not in result:
        return None
    for entry in result['requested_formats']:
        # the resolver marks not all entries with video AND audio 
        # but usually adaptive video streams also have audio
        if 'manifest_url' in entry and 'vcodec' in entry and get_adaptive_type_from_url(entry['manifest_url']):
            return entry['manifest_url']
    return None


def extract_best_all_in_one_stream(result):
    # if there is nothing to choose from simply take the shot it is correct
    if len(result['formats']) == 1:
        return result['formats'][0]['url'] 
    audio_video_streams = [] 
    filter_format = (lambda f: f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none')
    # assume it is a video containg audio. Get the one with the highest resolution
    for entry in result['formats']:
        if filter_format(entry):
            audio_video_streams.append(entry)
    if audio_video_streams:
            return max(audio_video_streams, key=lambda f: f['width'])['url'] 
    # test if it is an audio only stream
    if result.get('vcodec', 'none') == 'none': 
        # in case of multiple audio streams get the best
        audio_streams = []
        filter_format = (lambda f: f.get('abr', 'none') != 'none')
        for entry in result['formats']:
            if filter_format(entry):
                audio_streams.append(entry)
        if audio_streams:
            return max(audio_streams, key=lambda f: f['abr'])['url'] 
        # not all extractors provide an abr (and other fields are also not guaranteed), try to get any audio 
        if (entry.get('acodec', 'none') != 'none') or entry.get('ext', False) in ['mp3', 'wav', 'opus']:
            return entry['url']      
    # was not able to resolve
    return None

def get_adaptive_type_from_url(url):
    supported_endings = [".m3u8", ".hls", ".mpd", ".rtmp", ".ism"]
    file = url.split('/')[-1]
    for ending in supported_endings:
        if ending in file:
            # adaptive input stream plugin needs the type which is not the same as the file ending
            if ending  == ".m3u8":  
                return "hls"
            else:
                return ending.lstrip('.')
    log("Manifest type could not be identified for {}".format(file))
    return False

def check_if_kodi_supports_manifest(url):
    from inputstreamhelper import Helper
    adaptive_type = get_adaptive_type_from_url(url)
    is_helper = Helper(adaptive_type) 
    supported = is_helper.check_inputstream()
    if not supported:
        msg = "your kodi instance does not support the adaptive stream manifest of " + url + ", might need to install the adpative stream plugin"
        showInfoNotification("msg")
        log(msg=msg, level=xbmc.LOGWARNING)
    return adaptive_type, supported

def createListItemFromVideo(result):
    debug(result)
    adaptive_type = False
    if xbmcplugin.getSetting(int(sys.argv[1]),"usemanifest") == 'true':
        url = extract_manifest_url(result)
        if url is not None:
            log("found original manifest: " + url)
            adaptive_type, supported = check_if_kodi_supports_manifest(url)
            if not supported:
                url = None 
        if url is None:
            log("could not find an original manifest or manifest is not supported falling back to best all-in-one stream")
            url = extract_best_all_in_one_stream(result)
        if url is None:
            err_msg = "Error: was not able to extract manifest or all-in-one stream. Implement https://github.com/firsttris/plugin.video.sendtokodi/issues/34"
            log(err_msg)
            showInfoNotification(err_msg)
            raise Exception(err_msg)
    else:
        url = result['url']
    log("creating list item for url {}".format(url))
    list_item = xbmcgui.ListItem(result['title'], path=url)
    list_item.setInfo(type='Video', infoLabels={'Title': result['title'], 'plot': result.get('description', None)})
    if result.get('thumbnail', None) is not None:
        list_item.setArt({'thumb': result['thumbnail']})
    subtitles = result.get('subtitles', {})
    if subtitles:
        list_item.setSubtitles([
            subtitleListEntry['url']
            for lang in subtitles
            for subtitleListEntry in subtitles[lang]
        ])
    if adaptive_type:
        list_item.setProperty('inputstream', 'inputstream.adaptive')
        list_item.setProperty('inputstream.adaptive.manifest_type', adaptive_type)


    return list_item

def createListItemFromFlatPlaylistItem(video):
    listItemUrl = __url__ + "?" + video['url']
    title = video['title'] if 'title' in video else video['url']

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

# get the index of the first video to be played in the submitted playlist url
def playlistIndex(url, playlist):
    if sys.version_info[0] >= 3:
        from urllib.parse import urlparse, parse_qs
    else:
        from urlparse import urlparse, parse_qs 
    
    query = urlparse(url).query
    queryParams = parse_qs(query)
    
    if 'v' not in queryParams:
        return None
    
    v = queryParams['v'][0]
    
    try:
        # youtube playlist indices start at 1
        index = int(queryParams.get('index')[0]) - 1
        if playlist['entries'][index]['id'] == v:
            return index
    except:
        pass
    
    for i, entry in enumerate(playlist['entries']):
        if entry['id'] == v:
            return i
    
    return None


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
if xbmcplugin.getSetting(int(sys.argv[1]),"usemanifest") == 'true':
    ydl_opts['format'] = 'bestvideo*+bestaudio/best'
ydl = YoutubeDL(ydl_opts)
ydl.add_default_info_extractors()

with ydl:
    progress = xbmcgui.DialogProgressBG()
    progress.create("Resolving " + url)
    try:
        result = ydl.extract_info(url, download=False)
    except:
        progress.close()
        showErrorNotification("Could not resolve the url, check the log for more info")
        import traceback
        log(msg=traceback.format_exc(), level=xbmc.LOGERROR)
        exit()
    progress.close()

if 'entries' in result:
    # more than one video
    pl = xbmc.PlayList(1)
    pl.clear()

    # determine which index in the queue to start playing from
    indexToStartAt = playlistIndex(url, result)
    if indexToStartAt == None:
        indexToStartAt = 0

    unresolvedEntries = list(result['entries'])
    startingEntry = unresolvedEntries.pop(indexToStartAt)

    # populate the queue with unresolved entries so that the starting entry can be inserted
    for video in unresolvedEntries:
        list_item = createListItemFromFlatPlaylistItem(video)
        pl.add(list_item.getPath(), list_item)

    # make sure the starting ListItem has a resolved url, to avoid recursion and crashes
    startingVideoUrl = startingEntry['url']
    startingItem = createListItemFromVideo(ydl.extract_info(startingVideoUrl, download=False))
    pl.add(startingItem.getPath(), startingItem, indexToStartAt)
    
    #xbmc.Player().play(pl) # this probably works again
    # ...but start playback the same way the Youtube plugin does it:
    xbmc.executebuiltin('Playlist.PlayOffset(%s,%d)' % ('video', indexToStartAt))

    showInfoNotification("Playing playlist " + result['title'])
else:
    # Just a video, pass the item to the Kodi player.
    showInfoNotification("Playing title " + result['title'])
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=createListItemFromVideo(result))