from typing import Any, Callable
from rcc.communications.client.dbus.abstract_dbus_client import AbstractDbusClient
from framework.singleton import singleton


@singleton
class UpowerClient(AbstractDbusClient):
    """Dbus upower client"""

    def __init__(self):
        super().__init__(
            True,
            "org.freedesktop.UPower",
            "/org/freedesktop/UPower",
            "org.freedesktop.UPower",
        )

    @property
    def on_battery(self) -> bool:
        """Battery flag"""
        return self._get_property("OnBattery")

    def on_battery_change(self, callback: Callable[[Any], None]):
        """Subscribe ac or battery changes"""
        self.on_property_change("OnBattery", callback)


UPOWER_CLIENT = UpowerClient()
