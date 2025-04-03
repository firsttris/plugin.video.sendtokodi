# -*- coding: utf-8 -*-
import sys
import os

# Ensures yt-dlp is on the python path
# Workaround for issue caused by upstream commit
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{dir_path}/lib/")

import json
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


def guess_manifest_type(f, url):
    protocol = f.get('protocol', "")
    if protocol.startswith("m3u"):
        return "hls"
    elif protocol.startswith("rtmp") or protocol == "rtsp":
        return "rtmp"
    elif protocol == "ism":
        return "ism"
    for s in [".m3u", ".m3u8", ".hls", ".mpd", ".rtmp", ".ism"]:
        offset = url.find(s, 0)
        while offset != -1:
            if offset == len(url) - len(s) or not url[offset + len(s)].isalnum():
                if s.startswith("m3u"):
                    s = ".hls"
                return s[1:]
            offset = url.find(s, offset + 1)
    return None

try:
    import inputstreamhelper

    def isa_supports(stream):
        if stream is None or len(stream) < 1:
            return False
        return inputstreamhelper.Helper(stream).check_inputstream()
except ImportError:
    def isa_supports(stream):
        return False

def createListItemFromVideo(result):
    debug(result)

    url = None
    isa = None
    headers = None

    # first try existing manifest
    manifest_url = result.get('manifest_url') if usemanifest else None
    if manifest_url is not None and isa_supports(guess_manifest_type(result, manifest_url)):
        isa = True
        url = manifest_url
        headers = result.get('http_headers')
        log("Picked original manifest")

    # then move on to heuristic format selection
    if url is None:
        have_video = False
        have_audio = False
        dash_video = []
        dash_audio = []
        filtered_format = None
        all_formats = result.get('formats', [])
        for f in all_formats:
            vcodec = f.get('vcodec', "none")
            acodec = f.get('acodec', "none")
            if vcodec != "none":
                have_video = True
            if acodec != "none":
                have_audio = True

            container = f.get('container', "")
            if vcodec != "none" and acodec == "none" and container in ["mp4_dash", "webm_dash"]:
                dash_video.append(f)
            if vcodec == "none" and acodec != "none" and container in ["m4a_dash", "webm_dash"]:
                dash_audio.append(f)

        # workaround for unknown ISA bug that causes audio to fail when
        # multiple streams are available, though seemingly only when they have
        # different sample rates.
        if len(dash_audio) > 1:
            dash_audio = [dash_audio[-1]]

        # ytdl returns formats from worst to best
        for f in reversed(all_formats):
            # assume that manifests are either video+audio regardless of acodec, or audio only
            vcodec = f.get('vcodec')
            acodec = f.get('acodec')
            if (have_video and vcodec == "none") or (not have_video and acodec == "none"):
                continue

            # Streams with adaptive manifests:
            # ytdl will sometimes return a manifest_url in individual formats
            # but not a global one. When this happens it (always?) means that
            # it's functionally a global manifest.
            manifest_url = f.get('manifest_url') if usemanifest else None
            if manifest_url is not None and isa_supports(guess_manifest_type(f, manifest_url)):
                url = manifest_url
                isa = True
                headers = f.get('http_headers')
                log("Picked format " + f.get('format', "") + " manifest")
                break

            # MPEG-DASH streams without adaptive manifest:
            if usedashbuilder and (not have_video or len(dash_video) > 0) and (not have_audio or len(dash_audio) > 0) and ((have_video and f == dash_video[-1]) or (not have_video and have_audio and f == dash_audio[-1])) and isa_supports("mpd"):
                import dash_builder
                builder = dash_builder.Manifest(result.get('duration', "0"))
                video_success = not have_video
                audio_success = not have_audio
                for fvideo in dash_video:
                    fid = fvideo.get('format', "")
                    try:
                        builder.add_video_format(fvideo)
                        video_success = True
                        log("Added video stream {} to DASH manifest".format(fid))
                    except Exception as e:
                        log("Failed to add DASH video stream {}: {}".format(fid, e))
                for faudio in dash_audio:
                    fid = faudio.get('format', "")
                    try:
                        builder.add_audio_format(faudio)
                        audio_success = True
                        log("Added audio stream {} to DASH manifest".format(fid))
                    except Exception as e:
                        log("Failed to add DASH audio stream {}: {}".format(fid, e))
                if video_success and audio_success:
                    url = dash_builder.start_httpd(builder.emit())
                    isa = True
                    headers = f.get('http_headers')
                    log("Picked DASH with custom manifest")
                    break

            # Non-adaptive manifests or files on servers:
            if not 'url' in f:
                continue
            # TODO: implement support for making/serving global HLS manifests for m3u8 and mp4 urls
            if (have_video and vcodec == "none") or (have_audio and acodec == "none"):
                continue
            manifest_type = guess_manifest_type(f, f['url'])
            if manifest_type is not None and not isa_supports(manifest_type):
                continue
            width = f.get('width', 0)
            if width is not None and width > maxwidth:
                if filtered_format is None:
                    filtered_format = f
                continue
            url = f['url']
            isa = isa_supports(manifest_type)
            headers = f.get('http_headers')
            log("Picked raw format " + f.get('format', ""))
            break

        # if nothing could be selected, try playing anything we can
        if url is None and filtered_format is not None:
            url = filtered_format['url']
            isa = isa_supports(guess_manifest_type(filtered_format, url))
            headers = f.get('http_headers')

    if url is None:
        # yeah we're definitely cooked
        url = result.get('url')
        if url is not None:
            isa = isa_supports(guess_manifest_type(result, url))
            headers = result.get('http_headers')

    if url is None:
        msg = "No supported streams found"
        showErrorNotification(msg)
        raise Exception("Error: " + msg)

    log("creating list item for url {}".format(url))
    list_item = xbmcgui.ListItem(result['title'], path=url)
    video_info = list_item.getVideoInfoTag()
    video_info.setTitle(result['title'])
    video_info.setPlot(result.get('description', None))
    if result.get('thumbnail', None) is not None:
        list_item.setArt({'thumb': result['thumbnail']})
    subtitles = result.get('subtitles', {})
    if subtitles:
        list_item.setSubtitles([
            subtitleListEntry['url']
            for lang in subtitles
            for subtitleListEntry in subtitles[lang]
        ])
    if isa:
        list_item.setProperty('inputstream', 'inputstream.adaptive')

        # Many sites will throw a 403 unless the http headers (e.g. user agent and referer)
        # sent when downloading a manifest and streaming match those originally sent by yt-dlp.
        if headers is None:
            headers = result.get('http_headers')
        if headers is not None:
            from urllib.parse import urlencode
            headers = urlencode(headers)
            list_item.setProperty('inputstream.adaptive.manifest_headers', headers)
            list_item.setProperty('inputstream.adaptive.stream_headers', headers)

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

    video_info = listItem.getVideoInfoTag()
    video_info.setTitle(title)

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

# Open the settings if no parameters have been passed. Prevents crash.
# This happens when the addon is launched from within the Kodi OSD.
if not sys.argv[2]:
    xbmcaddon.Addon().openSettings()
    exit()
    
# Use the chosen resolver while forcing to use youtube_dl on legacy python 2 systems (dlp is python 3.6+)
if xbmcplugin.getSetting(int(sys.argv[1]),"resolver") == "0" or sys.version_info[0] == 2:
    from youtube_dl import YoutubeDL
else:
   # import lib.yt_dlp as yt_dlp
    from yt_dlp import YoutubeDL
    
# patch broken strptime (see above)
patch_strptime()

# extract_flat:  Do not resolve URLs, return the immediate result.
#                Pass in 'in_playlist' to only show this behavior for
#                playlist items.
ydl_opts = {
    'format': 'bv*+ba/b',
    'extract_flat': 'in_playlist'
}

params = getParams()
url = str(params['url'])
ydl_opts.update(params['ydlOpts'])

usemanifest = xbmcplugin.getSetting(int(sys.argv[1]),"usemanifest") == 'true'
usedashbuilder = (xbmcplugin.getSetting(int(sys.argv[1]),"usedashbuilder") == 'true') and (sys.version_info[0] >= 3)
maxwidth = int(xbmcplugin.getSetting(int(sys.argv[1]), "maxresolution"))

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
        if 'url' in video:
            list_item = createListItemFromFlatPlaylistItem(video)
            pl.add(list_item.getPath(), list_item)

    # make sure the starting ListItem has a resolved url, to avoid recursion and crashes
    if 'url' in startingEntry:
        startingItem = createListItemFromVideo(ydl.extract_info(startingEntry['url'], download=False))
    else:
        startingItem = createListItemFromVideo(startingEntry)
    pl.add(startingItem.getPath(), startingItem, indexToStartAt)
    
    #xbmc.Player().play(pl) # this probably works again
    # ...but start playback the same way the Youtube plugin does it:
    xbmc.executebuiltin('Playlist.PlayOffset(%s,%d)' % ('video', indexToStartAt))
else:
    # Just a video, pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=createListItemFromVideo(result))
