# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from unittest.mock import call
from unittest.mock import Mock
from unittest.mock import patch

from colcon_core.event.job import JobProgress
from colcon_core.event.job import JobStarted
from colcon_core.event.output import StdoutLine
from colcon_core.event.timer import TimerEvent
from colcon_core.executor import Job
from colcon_notification.event_handler.status import StatusEventHandler


def test_status_event_handler():
    with patch('sys.stdout') as stdout:
        stdout.isatty.return_code = True
        stdout_write = stdout.write

        job = Job(
            identifier='id', dependencies=set(),
            task=Mock(), task_context=Mock())
        job.task.context = job.task_context
        job.task_context.name = job.identifier
        job.task_context.pkg.name = job.identifier

        extension = StatusEventHandler()
        assert extension.enabled

        event = JobStarted(job.identifier)
        extension((event, job))

        event = JobProgress(job.identifier, 'bar')
        extension((event, job))

        event = StdoutLine(b'[  5%] baz')
        extension((event, job))

        event = TimerEvent()
        extension((event, None))
        assert stdout_write.call_args_list[-2:] == [
            call('[0.0s] [0/0 complete] [id:bar 5% - 0.0s]'),
            call('\r'),
        ]
        stdout_write.reset_mock()

        event = StdoutLine(b'[1/10] baz')
        extension((event, job))

        event = TimerEvent()
        extension((event, None))
        assert stdout_write.call_args_list[-2:] == [
            call('[0.0s] [0/0 complete] [id:bar 10% - 0.0s]'),
            call('\r'),
        ]
        stdout_write.reset_mock()

        event = StdoutLine(b'[ 15%] [1/10] ')
        extension((event, job))

        event = TimerEvent()
        extension((event, None))
        assert stdout_write.call_args_list[-2:] == [
            call('[0.0s] [0/0 complete] [id:bar 15% - 0.0s]'),
            call('\r'),
        ]
        stdout_write.reset_mock()
