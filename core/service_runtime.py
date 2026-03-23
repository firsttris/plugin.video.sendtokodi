import sys


class replacement_stderr(sys.stderr.__class__):
    def isatty(self):
        return False


def install_stderr_workaround():
    sys.stderr.__class__ = replacement_stderr


# python embedded (as used in kodi) has a known bug for second calls of strptime.
# The python bug is docmumented here https://bugs.python.org/issue27400
# The following workaround patch is borrowed from https://forum.kodi.tv/showthread.php?tid=112916&pid=2914578#pid2914578
def patch_strptime():
    import datetime

    class proxydt(datetime.datetime):
        @staticmethod
        def strptime(date_string, format):
            import time
            return datetime.datetime(*(time.strptime(date_string, format)[0:6]))

    datetime.datetime = proxydt
