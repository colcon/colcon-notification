# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from colcon_notification.desktop_notification \
    import DesktopNotificationExtensionPoint


class Notify2DesktopNotification(DesktopNotificationExtensionPoint):
    """Use `notify2` to show notifications."""

    # the priority is higher then 'notify_send' extension
    PRIORITY = 200

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            DesktopNotificationExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

        try:
            import notify2  # noqa: F401
        except ImportError:
            raise SkipExtensionException("'notify2' not found")

        self._initialized = False
        self._last_notification = None

    def notify(self, *, title, message, icon_path=None):  # noqa: D102
        import notify2

        if not self._initialized:
            notify2.init('colcon')
            self._initialized = True

        if self._last_notification is None:
            self._last_notification = notify2.Notification(
                title, message=message, icon=icon_path)
        else:
            self._last_notification.update(
                title, message=message, icon=icon_path)
        self._last_notification.show()
