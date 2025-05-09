from framework.singleton import singleton
from rcc.communications.client.dbus.asus.armoury.armoury_base_client import ArmouryBaseClient


@singleton
class NvBoostClient(ArmouryBaseClient):
    """DBus platform client"""

    def __init__(self):
        super().__init__("nv_dynamic_boost", False)


NV_BOOST_CLIENT = NvBoostClient()
