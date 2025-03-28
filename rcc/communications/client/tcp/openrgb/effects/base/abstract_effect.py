import time

from abc import ABC, abstractmethod
from threading import Lock, Thread
from typing import List, Optional

from rcc.communications.client.tcp.openrgb.client.orgb import Device
from rcc.communications.client.tcp.openrgb.client.utils import RGBColor

from rcc.models.rgb_brightness import RgbBrightness
from framework.logger import Logger


class AbstractEffect(ABC):
    """Base class for effects"""

    # Map brightness levels
    BRIGHTNESS_MAP = {
        RgbBrightness.OFF: 0,
        RgbBrightness.LOW: 0.25,
        RgbBrightness.MEDIUM: 0.5,
        RgbBrightness.HIGH: 0.75,
        RgbBrightness.MAX: 1,
    }

    def __init__(self, name: str, default_color: str = None):
        self._is_running = False
        self._brightness = 0
        self._supports_color = default_color is not None
        self._name = name
        self._color = RGBColor.fromHEX(default_color) if default_color is not None else None
        self._logger = Logger()
        self._mutex = Lock()
        self._devices: List[Device] = []
        self._thread = None
        self._brightness_changed = False

    def start(self, devices: List[Device], brightness: RgbBrightness, color: RGBColor):
        """Start effect"""
        if self._is_running:
            self.stop()

        self._thread = None
        self._is_running = True

        self._color = color
        self._devices = devices
        self._logger.info(
            f"Starting effect with {brightness.name.lower()} brightness"
            f"{' and ' + color.to_hex() + ' color' if self._supports_color else ''}"
        )

        self._brightness = self.BRIGHTNESS_MAP.get(brightness, 0)

        self._is_running = True

        self._thread = Thread(name=self.__class__.__name__, target=self._thread_main)
        self._thread.start()

    def stop(self):
        """Stop effect"""
        if self._is_running:
            self._logger.info("Stopping effect")
            self._is_running = False

            if self._thread is not None:
                self._thread.join()

    def _sleep(self, ms: float):
        naps = []
        while ms > 0:
            nap = min(0.1, ms)
            ms -= nap
            naps.append(nap)
        for nap in naps:
            if self._brightness_changed:
                self._brightness_changed = False
                break
            if self._is_running:
                time.sleep(nap)

    def _set_colors(self, dev: Device, colors: List[RGBColor]):
        if self._is_running:
            with self._mutex:
                if self._is_running:
                    dimmed_colors = [color * self._brightness for color in colors]
                    dev.set_colors(dimmed_colors, True)

    @property
    def supports_color(self) -> bool:
        """Check if effect supports color"""
        return self._supports_color

    @property
    def name(self) -> str:
        """Get effect name"""
        return self._name

    @property
    def color(self) -> Optional[str]:
        """Get hex color or none"""
        return self._color.to_hex() if self._supports_color else None

    @property
    def brightness(self) -> RgbBrightness:
        """Brightness of effect"""
        for k, v in self.BRIGHTNESS_MAP.items():
            if v == self._brightness:
                return k
        return RgbBrightness.MAX

    @brightness.setter
    def brightness(self, brightness: RgbBrightness):
        self._brightness = self.BRIGHTNESS_MAP.get(brightness, 0)
        self._logger.info(f"Updating effect with {brightness.name.lower()} brightness")
        self._brightness_changed = True

    def _thread_main(self):
        self.apply_effect()
        self._logger.info("Effect finished")
        self._thread = None

    @abstractmethod
    def apply_effect(self):
        """Apply effect"""
