# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
import platform
import subprocess

from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from colcon_notification.desktop_notification \
    import DesktopNotificationExtensionPoint
from pkg_resources import iter_entry_points

logger = colcon_logger.getChild(__name__)


class TerminalNotifierDesktopNotification(DesktopNotificationExtensionPoint):
    """Use `colcon-terminal-notifier` to show notifications."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            DesktopNotificationExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

        if platform.system() != 'Darwin':
            raise SkipExtensionException('Not used on non-Darwin systems')

    def notify(self, *, title, message, icon_path=None):  # noqa: D102
        if title.startswith('-'):
            title = '\\' + title
        if message.startswith('-'):
            message = '\\' + message

        entry_points = list(iter_entry_points(
            'colcon_notification.desktop_notification',
            name='terminal_notifier'))
        if not entry_points:
            logger.error(
                "Failed to find entry point of 'terminal_notifier'")
            return

        # determine the install prefix of this Python package
        install_prefix = Path(entry_points[0].dist.location)
        while install_prefix.name and install_prefix.name.lower() != 'lib':
            install_prefix = install_prefix.parent
        if install_prefix.name.lower() != 'lib':
            logger.error(
                'Could not determine the install prefix of the '
                'colcon-terminal-notifier.app')
            return

        cmd = [
            'open',
            str(
                install_prefix.parent / 'share' / 'colcon-notification' /
                'colcon-terminal-notifier.app'),
            '--args',
            '-message', message,
            '-title', title,
            '-group', 'colcon_pid_' + str(os.getpid()),
        ]
        if icon_path:
            cmd += ['--icon', icon_path]

        try:
            subprocess.run(cmd, input=message.encode())
        except FileNotFoundError as e:
            logger.error(
                "Failed to find 'colcon-terminal-notifier'")
        except subprocess.CalledProcessError as e:
            cmd_str = ' '.join(cmd)
            logger.error(
                "Failed to invoke '{cmd_str}'".format_map(locals()))
