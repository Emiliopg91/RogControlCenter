from dataclasses import dataclass
import math
import random
import threading

from openrgb.orgb import Device, Zone
from openrgb.utils import RGBColor, ZoneType, DeviceType

import psutil
from framework.singleton import singleton

from rcc.communications.client.tcp.openrgb.effects.base.abstract_effect import AbstractEffect


@dataclass
class LedStatus:
    """Led status holder class"""

    pos_idx: int = -1
    max_val: int = 20
    cur_val: int = 0

    def clone(self):
        """Copy self instance into new one"""
        return LedStatus(self.pos_idx, self.max_val, self.cur_val)


@singleton
class DigitalRain(AbstractEffect):
    """Digital rain effect"""

    def __init__(self):
        super().__init__("Digital rain", "#00FF00")
        self._max_count = 15
        self._cpu = 0
        self._nap_time = 0.07
        self._lock = threading.Lock()

        self.sin_array = [0] * int(2 * self._max_count / 3)

        # Rellenar el resto del array con valores basados en la función seno
        for i in range(int(2 * self._max_count / 3)):  # Desde la posición 1 hasta la 8
            x = (i / (self._max_count + 2)) * math.pi / 2  # Escalar el índice entre 0 y 1
            self.sin_array[i] = math.pow(math.sin(x), 2)

    def _decrement_matrix(self, zone_status: list[list[LedStatus]]):
        for r in range(len(zone_status) - 1, -1, -1):  # pylint: disable=
            for c in range(len(zone_status[0])):
                if r == 0:
                    if zone_status[r][c].cur_val > 0:
                        zone_status[r][c].cur_val = zone_status[r][c].cur_val - 1
                    elif zone_status[r][c].cur_val < 0:
                        zone_status[r][c].cur_val += 1
                else:
                    pos = zone_status[r][c].pos_idx
                    zone_status[r][c] = zone_status[r - 1][c].clone()
                    zone_status[r][c].pos_idx = pos

    def _to_color_matrix(self, zone_status: list[list[LedStatus]], dev_size: int):
        colors = [RGBColor(0, 0, 0) for _ in range(dev_size)]
        for _, row in enumerate(zone_status):  # Reemplazamos range(len(zone_status)) por enumerate
            for _, led in enumerate(row):  # Reemplazamos range(len(zone_status[0])) por enumerate
                if led.pos_idx >= 0:
                    if led.cur_val >= 0:
                        if led.cur_val == led.max_val:
                            colors[led.pos_idx] = RGBColor(255, 255, 255)
                        elif led.cur_val >= int(2 * led.max_val / 3):
                            colors[led.pos_idx] = self._color
                        else:
                            colors[led.pos_idx] = self._color * (
                                self.sin_array[round(led.cur_val * (led.max_val / self._max_count))]
                            )
                    else:
                        colors[led.pos_idx] = RGBColor(0, 0, 0)
        return colors

    def _is_matrix_column_available(self, zone_status: list[list[LedStatus]], height: int, column: int):
        for r in range(min(3, height)):
            if zone_status[r][column].cur_val != 0:
                return False
        return True

    def _is_matrix_column_not_last_elem_only(self, zone: Zone, height: int, column: int):
        if zone.matrix_map[height - 1][column] is None:
            return False

        for i in range(height - 1):
            if zone.matrix_map[i][column] is not None:
                return False

        return True

    def _get_next_matrix(self, zone_status: list[list[LedStatus]], hue: int):  # pylint: disable=too-many-branches
        free_cols: list[int] = []
        for c in range(len(zone_status[0])):
            if self._is_matrix_column_available(zone_status, len(zone_status), c):
                free_cols.append(c)

        if len(free_cols) > 0:
            allowed = max(1, math.ceil(len(zone_status[0]) * self._cpu))

            if allowed > len(zone_status[0]) - len(free_cols):
                next_col = free_cols[random.randint(0, len(free_cols) - 1)]
                zone_status[0][next_col].max_val = round(self._max_count * (1 - (0.25 * self._cpu)))
                zone_status[0][next_col].cur_val = zone_status[0][next_col].max_val

        return (hue + 51) % 360

    def _dev_to_mat(self, dev: Device) -> list[list[LedStatus]]:  # pylint: disable=too-many-branches,too-many-locals
        mat_def: list[list[LedStatus]] = []

        offset = 0
        last_leds = 0
        for zone in dev.zones:  # pylint: disable=too-many-nested-blocks
            if zone.type == ZoneType.MATRIX:
                has_only_last = False
                for r in range(zone.mat_height):
                    row = []
                    for c in range(zone.mat_width):
                        if zone.matrix_map[r][c] is not None:
                            row.append(LedStatus(pos_idx=offset + zone.matrix_map[r][c]))
                        else:
                            row.append(LedStatus(pos_idx=-1))
                    mat_def.append(row)

                    has_only_last = any(
                        self._is_matrix_column_not_last_elem_only(zone, zone.mat_height, col)
                        for col in range(zone.mat_width)
                    )

                only_last_cols = []
                if has_only_last:
                    for c in range(zone.mat_width):
                        if self._is_matrix_column_not_last_elem_only(zone, zone.mat_height, c):
                            only_last_cols.append(c)

                    new_mat: list[list[LedStatus]] = []
                    for r in range(zone.mat_height):
                        new_mat.append([])
                        for c in range(zone.mat_width):
                            if c not in only_last_cols:
                                new_mat[r].append(mat_def[r][c])

                    for c in range(len(new_mat[0])):
                        new_mat[len(new_mat) - 1][c].pos_idx = mat_def[len(mat_def) - 1][0].pos_idx + round(
                            c * ((len(mat_def[0]) - 1) / ((len(new_mat[0]) - 1)))
                        )

                    mat_def = new_mat
            else:
                row = []
                for l in range(len(zone.leds)):
                    row.append(LedStatus(pos_idx=offset + l))

                mat_def.append(row)

            offset += len(zone.leds)
            last_leds = len(zone.leds)

        if dev.type == DeviceType.MOUSE:
            offset -= last_leds
            for r, row in enumerate(mat_def):
                for c, led in enumerate(row):
                    led.pos_idx = abs(led.pos_idx - offset)

        return mat_def

    def apply_effect(self):
        def device_thread(dev: Device):
            zone_status: list[list[LedStatus | list[LedStatus]]] = self._dev_to_mat(dev)
            self._set_colors(dev, [RGBColor(0, 0, 0) for _ in dev.colors])
            self._sleep(random.randint(0, 500) / 1000)

            hue = random.randint(0, 359)

            while self._is_running and dev.enabled:
                self._decrement_matrix(zone_status)
                hue = self._get_next_matrix(zone_status, hue)
                final_colors = self._to_color_matrix(zone_status, len(dev.colors))

                self._set_colors(dev, final_colors)
                self._sleep(self._nap_time * (1 - 0.4 * self._cpu))

        def cpu_thread():
            while True:
                self._cpu = max(1, psutil.cpu_percent()) / 100
                if not self._is_running:
                    break
                self._sleep(2 * self._nap_time)

        threads = []
        thread = threading.Thread(name="DigitalRain-cpu", target=cpu_thread)
        threads.append(thread)
        thread.start()
        for dev_id, dev in enumerate(self._devices):
            thread = threading.Thread(
                name=f"DigitalRain-dev-{dev_id}",
                target=device_thread,
                args=[dev],
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


DIGITAL_RAIN_EFFECT = DigitalRain()
