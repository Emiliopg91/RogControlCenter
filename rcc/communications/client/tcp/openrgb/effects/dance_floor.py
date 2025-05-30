import random
from openrgb.utils import RGBColor

from framework.singleton import singleton
from rcc.communications.client.tcp.openrgb.effects.base.abstract_effect import AbstractEffect


@singleton
class DanceFloor(AbstractEffect):
    """Dance floor effect"""

    def __init__(self):
        super().__init__("Dance floor")

    def _get_random(self, length):
        randoms = []
        for _ in range(length):
            randoms.append(RGBColor.fromHSV(random.randint(0, 359), random.randint(0, 20) + 80, 100))
        return randoms

    def apply_effect(self):
        while self._is_running:
            for dev in self._devices:
                if dev.enabled:
                    self._set_colors(dev, self._get_random(len(dev.colors)))
            self._sleep(0.5)  # 500 ms


DANCE_FLOOR_EFFECT = DanceFloor()
