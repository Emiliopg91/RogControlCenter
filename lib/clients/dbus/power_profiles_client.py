from lib.clients.dbus.base.abstract_dbus_client import AbstractDbusClient
from lib.models.power_profile import PowerProfile
from lib.utils.singleton import singleton


@singleton
class PowerProfilesClient(AbstractDbusClient):
    """DBus power profile client"""

    def __init__(self):
        super().__init__(
            True,
            "net.hadess.PowerProfiles",
            "/net/hadess/PowerProfiles",
            "net.hadess.PowerProfiles",
        )

    @property
    def active_profile(self) -> PowerProfile:
        """Active power profile"""
        return PowerProfile(self.get_property("ActiveProfile"))

    @active_profile.setter
    def active_profile(self, val: PowerProfile) -> None:
        self.set_property("ActiveProfile", val.value)


power_profile_client = PowerProfilesClient()
