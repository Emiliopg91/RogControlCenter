import math
import random
import threading

import psutil
from openrgb.orgb import Device
from openrgb.utils import RGBColor, ZoneType

from lib.clients.openrgb.effects.base.abstract_effect import AbstractEffect
from lib.utils.openrgb import OpenRGBUtils
from lib.utils.singleton import singleton


@singleton
class DigitalRain(AbstractEffect):
    """Digital rain effect"""

    def __init__(self):
        super().__init__("Digital rain", "#00FF00")
        self.decrement = 1.4
        self.max_count = int(pow(self.decrement, 10))
        self.matrix_on_rate = 0

    def _initialize_matrix(self, zone_status, zone):
        for i in range(zone.mat_height):
            zone_status.append([])
            for _ in range(zone.mat_width):
                zone_status[i].append(0)

    def _initialize_linear(self, zone_status, zone):
        for _ in range(len(zone.leds)):
            zone_status.append(0)

    def _decrement_matrix(self, zone_status, zone):
        for r in range(zone.mat_height - 1, -1, -1):
            for c in range(zone.mat_width):
                if r == 0:
                    if zone_status[r][c] > 0:
                        zone_status[r][c] = math.floor(zone_status[r][c] / self.decrement)
                else:
                    zone_status[r][c] = zone_status[r - 1][c]

    def _decrement_linear(self, zone_status, zone):
        for r in range(len(zone.leds) - 1, -1, -1):
            if r == 0:
                if zone_status[r] > 0:
                    zone_status[r] = math.floor(zone_status[r] / self.decrement)
            else:
                zone_status[r] = zone_status[r - 1]

    def _to_color_matrix(self, zone_status, zone):
        colors = [RGBColor(0, 0, 0) for _ in range(len(zone.leds))]
        for r in range(zone.mat_height):
            for c in range(zone.mat_width):
                if zone.matrix_map[r][c] is not None:
                    if zone_status[r][c] == self.max_count:
                        colors[zone.matrix_map[r][c]] = RGBColor(255, 255, 255)
                    else:
                        colors[zone.matrix_map[r][c]] = OpenRGBUtils.dim(
                            self._color, zone_status[r][c] / self.max_count
                        )
        return colors

    def _to_color_linear(self, zone_status, zone):
        colors = [RGBColor(0, 0, 0) for _ in range(len(zone.leds))]
        for r in range(len(zone.leds)):
            if zone_status[r] == self.max_count:
                colors[r] = RGBColor(255, 255, 255)
            else:
                colors[r] = OpenRGBUtils.dim(self._color, zone_status[r] / self.max_count)
        return colors

    def _get_next_matrix(self, status, zone):
        count_off = 0
        for c in range(zone.mat_width):
            for r in range(zone.mat_height):
                if status[r][c] != 0:
                    break
                count_off += 1
        if count_off / zone.mat_width > self.matrix_on_rate:
            next_col = -1
            iters = 0
            while next_col < 0:
                iters += 1
                next_col = math.floor(random.random() * zone.mat_width)
                for r in range(zone.mat_height):
                    if status[r][next_col] != 0:
                        next_col = -1
                    else:
                        status[0][next_col] = self.max_count

    def _get_next_linear(self, status, zone):
        count_off = sum(1 for c in status if c == 0)
        if count_off / len(zone.leds) > self.matrix_on_rate:
            next_idx = -1
            while next_idx < 0:
                next_idx = math.floor(random.random() * len(zone.leds))
                if status[next_idx] != 0:
                    next_idx = -1
                else:
                    status[next_idx] = self.max_count

    def apply_effect(self):
        zone_status = []
        colors = []
        threads = []

        def device_thread(dev: Device, dev_id):
            colors.append([RGBColor(0, 0, 0) for _ in dev.colors])
            self._set_colors(dev, colors[dev_id])

            for iz, zone in enumerate(dev.zones):
                zone_status[dev_id].append([])

                if zone.type == ZoneType.MATRIX:
                    self._initialize_matrix(zone_status[dev_id][iz], zone)
                elif zone.type in (ZoneType.LINEAR, ZoneType.SINGLE):
                    self._initialize_linear(zone_status[dev_id][iz], zone)

            self._sleep(random.randint(0, 100) / 1000)

            iter_count = 0
            while self.is_running:
                offset = 0
                final_colors = [RGBColor(0, 0, 0) for _ in dev.colors]
                cpu = psutil.cpu_percent() / 100
                for iz, zone in enumerate(dev.zones):
                    can_add = (iter_count % (8 - math.ceil(4 * cpu))) == 0
                    zone_colors = None

                    if zone.type == ZoneType.MATRIX:
                        self._decrement_matrix(zone_status[dev_id][iz], zone)
                        if can_add:
                            self._get_next_matrix(zone_status[dev_id][iz], zone)
                        zone_colors = self._to_color_matrix(zone_status[dev_id][iz], zone)
                    elif zone.type in (ZoneType.LINEAR, ZoneType.SINGLE):
                        self._decrement_linear(zone_status[dev_id][iz], zone)
                        if can_add:
                            self._get_next_linear(zone_status[dev_id][iz], zone)
                        zone_colors = self._to_color_linear(zone_status[dev_id][iz], zone)

                    for i, color in enumerate(zone_colors):
                        final_colors[offset + i] = color
                    offset += len(zone.leds)

                self._set_colors(dev, final_colors)
                self._sleep(((75 * (1 - (cpu * 0.4)) / 1000)))
                iter_count = (iter_count + 1) % 100

        for dev_id, dev in enumerate(self.devices):
            zone_status.append([])
            thread = threading.Thread(
                name=f"DigitalRain-dev-{dev_id}",
                target=device_thread,
                args=(dev, dev_id),
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


digital_rain = DigitalRain()
