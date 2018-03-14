# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import atexit
import re
import shutil
import sys
import time

from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobProgress
from colcon_core.event.job import JobQueued
from colcon_core.event.job import JobStarted
from colcon_core.event.output import StdoutLine
from colcon_core.event.timer import TimerEvent
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.plugin_system import satisfies_version


class StatusEventHandler(EventHandlerExtensionPoint):
    """
    Continuously update a status line.

    The extension handles events of the following types:
    - :py:class:`colcon_core.event.output.StdoutLine`
    - :py:class:`colcon_core.event.job.JobEnded`
    - :py:class:`colcon_core.event.job.JobProgress`
    - :py:class:`colcon_core.event.job.JobQueued`
    - :py:class:`colcon_core.event.job.JobStarted`
    - :py:class:`colcon_core.event.timer.TimerEvent`
    """

    # the priority should be lower than other extensions
    # in order to not update the status before they are finished
    PRIORITY = 50

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self._start_time = time.time()
        self._queued_count = 0
        self._running = {}
        self._ended = {}

        # pattern to match progress indicator in e.g. make
        self._progress_pattern = re.compile('^\[(  \d| \d\d|1\d\d)%\] ')

        # decorate write methods for stdout / stderr
        # to clear the last status line before other output
        sys.stdout.write = self._write_and_last_clear_status_line(
            sys.stdout.write)
        sys.stdout.buffer.write = self._write_and_last_clear_status_line(
            sys.stdout.buffer.write)
        sys.stderr.write = self._write_and_last_clear_status_line(
            sys.stderr.write)
        sys.stderr.buffer.write = self._write_and_last_clear_status_line(
            sys.stderr.buffer.write)
        self._last_status_line_length = None

        # register exit handle to ensure the last status line is cleared
        atexit.register(self._clear_last_status_line)

    def _write_and_last_clear_status_line(self, func):
        def wrapped_func(*args, **kwargs):
            self._clear_last_status_line()
            return func(*args, **kwargs)
        return wrapped_func

    def _clear_last_status_line(self):
        if self._last_status_line_length is not None:
            # overwrite last status message with spaces
            msg = ' ' * self._last_status_line_length + '\r'
            self._last_status_line_length = None
            sys.stdout.write(msg)

    def __call__(self, event):  # noqa: D102
        data = event[0]

        if isinstance(data, JobQueued):
            self._queued_count += 1

        elif isinstance(data, JobStarted):
            job = event[1]
            assert job not in self._running
            self._running[job] = {'start_time': time.time()}

        elif isinstance(data, JobProgress):
            job = event[1]
            self._running[job]['progress'] = [data.progress]

        elif isinstance(data, StdoutLine):
            line = data.line
            if isinstance(line, bytes):
                line = line.decode(errors='replace')
            match = self._progress_pattern.match(line)
            if not match:
                return
            job = event[1]
            progress = self._running[job].get('progress', [])
            while len(progress) > 1:
                progress.pop()
            progress.append(match.group(1).lstrip() + '%')

        elif isinstance(data, JobEnded):
            job = event[1]
            self._ended[job] = self._running[job]
            self._ended[job]['end_time'] = time.time()
            self._ended[job]['rc'] = data.rc
            del self._running[job]

        elif isinstance(data, TimerEvent):
            now = time.time()
            blocks = []

            # runtime in seconds
            blocks.append('[%.1fs]' % (now - self._start_time))

            # number of completed jobs / number of jobs
            blocks.append(
                '[%d/%d complete]' %
                (len(self._ended), self._queued_count))

            # number of failed jobs if not zero
            failed_jobs = [j for j, d in self._ended.items() if d['rc']]
            if failed_jobs:
                blocks.append('[%d failed]' % len(failed_jobs))

            # job identifier, label and time for ongoings jobs
            for job, d in self._running.items():
                msg = job.task.context.pkg.name
                if 'progress' in d:
                    msg += ':%s' % ' '.join(d['progress'])
                blocks.append('[%s - %.1fs]' % (msg, now - d['start_time']))

            # determine blocks which fit into terminal width
            max_width = shutil.get_terminal_size().columns
            for i in reversed(range(len(blocks))):
                msg = ' '.join(blocks[0:i + 1])
                # append dots when skipping at least one block
                if i < len(blocks) - 1:
                    msg += ' ...'
                if len(msg) < max_width:
                    break
            else:
                return

            print(msg, end='\r')
            self._last_status_line_length = len(msg)
