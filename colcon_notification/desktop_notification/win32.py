# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import sys
import time

from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from colcon_notification.desktop_notification \
    import DesktopNotificationExtensionPoint


class Win32DesktopNotification(DesktopNotificationExtensionPoint):
    """Use the Windows API to show notifications."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            DesktopNotificationExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

        if sys.platform != 'win32':
            raise SkipExtensionException('Not used on non-Windows systems')

        self._initialized = False
        self._last_notification = None

    def notify(self, *, title, message, icon_path=None):  # noqa: D102
        NotificationWindow(title, message, icon_path=icon_path)


class NotificationWindow:
    """Notification windows using the Win32 API."""

    def __init__(self, title, message, icon_path=None):  # noqa: D107
        import win32con
        import win32gui

        wc, class_atom = NotificationWindow._create_window_class()

        # create the window
        hwnd = win32gui.CreateWindow(
            NotificationWindow._class_atom,
            'Colcon notification',  # window class name
            win32con.WS_OVERLAPPED | win32con.WS_SYSMENU,  # style
            0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
            0, 0, NotificationWindow._wc.hInstance, None)
        win32gui.UpdateWindow(hwnd)

        # load icon image
        try:
            if icon_path is None:
                # use fall back
                raise Exception()
            hicon = win32gui.LoadImage(
                NotificationWindow._wc.hInstance, icon_path,
                win32con.IMAGE_ICON, 0, 0,
                win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,  # flags
            )
        except Exception:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        # show the notification
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (hwnd, 0, flags, win32con.WM_USER + 20, hicon, 'tooltip')
        win32gui.Shell_NotifyIcon(
            win32gui.NIM_ADD, nid)
        win32gui.Shell_NotifyIcon(
            win32gui.NIM_MODIFY, (
                hwnd, 0, win32gui.NIF_INFO, win32con.WM_USER + 20, hicon,
                'Balloon  tooltip', message, 200, title))

        # wait a while before destroying the window
        time.sleep(5)
        win32gui.DestroyWindow(hwnd)

    _wc = None
    _class_atom = None

    @staticmethod
    def _create_window_class():  # noqa: D102
        import win32api
        import win32con
        import win32gui

        # register the window class once
        if NotificationWindow._wc is None:
            NotificationWindow._wc = win32gui.WNDCLASS()
            NotificationWindow._wc.hInstance = win32api.GetModuleHandle(None)
            NotificationWindow._wc.lpszClassName = 'ColconTaskbar'
            NotificationWindow._wc.lpfnWndProc = {
                win32con.WM_DESTROY: NotificationWindow._on_destroy,
            }
            NotificationWindow._class_atom = win32gui.RegisterClass(
                NotificationWindow._wc)

        return (NotificationWindow._wc, NotificationWindow._class_atom)

    @staticmethod
    def _on_destroy(hwnd, msg, wparam, lparam):  # noqa: D102
        import win32gui
        nid = (hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)
