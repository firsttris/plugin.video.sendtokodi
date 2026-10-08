import sys


class replacement_stderr(sys.stderr.__class__):
    def isatty(self):
        return False


def install_stderr_workaround():
    if sys.stderr.__class__ is replacement_stderr:
        return
    sys.stderr.__class__ = replacement_stderr


# Kodi runs every add-on invocation in its own Python sub-interpreter and destroys it
# afterwards. Up to Python 3.12, the C datetime module caches the _strptime module in a
# static variable that is shared by all interpreters: the first interpreter that calls
# datetime.datetime.strptime() stores *its* module there. Once that interpreter is gone,
# the cached module's functions are None, and every later strptime() call in any
# add-on fails with "TypeError: 'NoneType' object is not callable" (issues #8, #177;
# https://bugs.python.org/issue27400, fixed in Python 3.13). yt-dlp calls strptime for
# upload dates and Last-Modified headers, so extraction breaks from the second
# invocation on, or right away if another add-on used strptime first.
# A one-time "warmup" call does not help: it fills the shared cache with this
# invocation's module, which breaks the next invocation. time.strptime() imports
# _strptime on every call, so routing datetime.strptime through it avoids the cache.
# Workaround from https://forum.kodi.tv/showthread.php?tid=112916&pid=2914578#pid2914578
def patch_strptime():
    import datetime

    # A reused interpreter runs this on every invocation; patch only once.
    if getattr(datetime.datetime, '_sendtokodi_strptime_patch', False):
        return

    class proxydt(datetime.datetime):
        _sendtokodi_strptime_patch = True

        @staticmethod
        def strptime(date_string, format):
            import time
            return datetime.datetime(*(time.strptime(date_string, format)[0:6]))

    datetime.datetime = proxydt
