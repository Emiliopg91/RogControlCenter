import os

from rcc import __app_name__
from rcc.communications.client.dbus.notification_client import notification_client
from rcc.utils.constants import icons_path
from framework.singleton import singleton


@singleton
class Notifier:
    """Class for showing notifications"""

    ICON_PATH = os.path.join(icons_path, "icon-45x45.png")

    def __init__(self):
        self.last_id = 0

    def show_toast(self, message, can_be_hidden=True, icon=ICON_PATH):
        """Show notification"""
        if self.last_id > 0:
            notification_client.close_notification(self.last_id)

        try:
            toast_id = notification_client.show_notification(__app_name__, icon, " ", message, 3000)
            if can_be_hidden:
                self.last_id = toast_id
        except Exception:
            """"""


notifier = Notifier()
