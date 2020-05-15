#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import errno
import logging
import logging.config
import logging.handlers
import os
import pyinotify
import stat
import time
try:
    import syslog
except ImportError:
    syslog = None

"""Linux specific pyinotify based logging handlers"""


class _FileKeeper(pyinotify.ProcessEvent):
    def my_init(self, watched_handler, watched_file):
        self._watched_handler = watched_handler
        self._watched_file = watched_file

    def process_default(self, event):
        if event.name == self._watched_file:
            self._watched_handler.reopen_file()


class _EventletThreadedNotifier(pyinotify.ThreadedNotifier):

    def loop(self):
        """Eventlet friendly ThreadedNotifier

        EventletFriendlyThreadedNotifier contains additional time.sleep()
        call insude loop to allow switching to other thread when eventlet
        is used.
        It can be used with eventlet and native threads as well.
        """

        while not self._stop_event.is_set():
            self.process_events()
            time.sleep(0)
            ref_time = time.time()
            if self.check_events():
                self._sleep(ref_time)
                self.read_events()


class FastWatchedFileHandler(logging.handlers.WatchedFileHandler, object):
    """Frequency of reading events.

    Watching thread sleeps max(0, READ_FREQ - (TIMEOUT / 1000)) seconds.
    """
    READ_FREQ = 5

    """Poll timeout in milliseconds.

    See https://docs.python.org/2/library/select.html#select.poll.poll"""
    TIMEOUT = 5

    def __init__(self, logpath, *args, **kwargs):
        self._log_file = os.path.basename(logpath)
        self._log_dir = os.path.dirname(logpath)
        super(FastWatchedFileHandler, self).__init__(logpath, *args, **kwargs)
        self._watch_file()

    def _watch_file(self):
        mask = pyinotify.IN_MOVED_FROM | pyinotify.IN_DELETE
        watch_manager = pyinotify.WatchManager()
        handler = _FileKeeper(watched_handler=self,
                              watched_file=self._log_file)
        notifier = _EventletThreadedNotifier(
            watch_manager,
            default_proc_fun=handler,
            read_freq=FastWatchedFileHandler.READ_FREQ,
            timeout=FastWatchedFileHandler.TIMEOUT)
        notifier.daemon = True
        watch_manager.add_watch(self._log_dir, mask)
        notifier.start()

    def reopen_file(self):
        try:
            # stat the file by path, checking for existence
            sres = os.stat(self.baseFilename)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sres = None
            else:
                raise
        # compare file system stat with that of our stream file handle
        if (not sres or
                sres[stat.ST_DEV] != self.dev or
                sres[stat.ST_INO] != self.ino):
            if self.stream is not None:
                # we have an open file handle, clean it up
                self.stream.flush()
                self.stream.close()
                self.stream = None
                # open a new file handle and get new stat info from that fd
                self.stream = self._open()
                self._statstream()
