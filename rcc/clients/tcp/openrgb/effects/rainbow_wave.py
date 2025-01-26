import math

# pylint: disable=E0611, E0401
from rcc.clients.tcp.openrgb.client.utils import RGBColor, ZoneType


from rcc.clients.tcp.openrgb.effects.base.abstract_effect import AbstractEffect
from rcc.utils.singleton import singleton


@singleton
class RainbowWave(AbstractEffect):
    """Rainbow wave effect"""

    def __init__(self):
        super().__init__("Rainbow wave")

    def apply_effect(self):
        longest_zone = max(set(max(set(zone.mat_width or len(zone.leds) for zone in el.zones)) for el in self._devices))
        inc = 12

        rainbow = [0] * longest_zone
        for idx in range(len(rainbow) - 1, -1, -1):
            rainbow[idx] = (len(rainbow) - idx) * inc

        while self._is_running:  # pylint: disable=R1702
            for dev in self._devices:
                colors = [RGBColor(0, 0, 0)] * len(dev.leds)
                offset = 0
                for zone in dev.zones:
                    if zone.type == ZoneType.MATRIX:
                        for r in range(zone.mat_height):
                            for c in range(zone.mat_width):
                                if zone.matrix_map[r][c] is not None:
                                    rainbow_index = math.floor(len(rainbow) * (c / zone.mat_width))
                                    colors[offset + zone.matrix_map[r][c]] = RGBColor.fromHSV(
                                        rainbow[rainbow_index], 100, 100
                                    )
                    else:
                        for l in range(len(zone.leds)):
                            rainbow_index = math.floor(len(rainbow) * (l / len(zone.leds)))
                            colors[offset + l] = RGBColor.fromHSV(rainbow[rainbow_index], 100, 100)
                    offset += len(zone.leds)
                self._set_colors(dev, colors)

            self._sleep(3 / longest_zone)

            for idx in range(len(rainbow) - 1, 0, -1):
                rainbow[idx] = rainbow[idx - 1]
            rainbow[0] = (rainbow[1] + inc) % 360


rainbow_wave = RainbowWave()
