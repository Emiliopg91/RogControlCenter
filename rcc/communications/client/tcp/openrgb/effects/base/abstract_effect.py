import time

from abc import ABC, abstractmethod
from threading import Lock, Thread
from typing import List, Optional

from openrgb.orgb import Device
from openrgb.utils import RGBColor

from rcc.models.rgb_brightness import RgbBrightness
from framework.logger import Logger


class AbstractEffect(ABC):
    """Base class for effects"""

    # Map brightness levels
    BRIGHTNESS_MAP = {
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

    def start(self, devices: List[Device], brightness: RgbBrightness, color: RGBColor):
        """Start effect"""
        if self._is_running:
            self.stop()

        self._thread = None
        self._is_running = True

        if brightness == RgbBrightness.OFF:
            self._logger.info("Turning off RGB")
            for dev in devices:
                dev.set_colors([RGBColor.fromHEX("#000000")] * len(dev.leds), True)
            return

        self._color = color
        self._devices = devices
        self._logger.info(
            f"Starting effect with {brightness.name.lower()} brightness"
            f"{' and ' + color.toHex() + ' color' if self._supports_color else ''}"
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
        return self._color.toHex() if self._supports_color else None

    def _thread_main(self):
        self.apply_effect()
        self._logger.info("Effect finished")
        self._thread = None

    @abstractmethod
    def apply_effect(self):
        """Apply effect"""
