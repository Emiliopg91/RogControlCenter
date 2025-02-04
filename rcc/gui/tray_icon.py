import os
import signal
import subprocess
import time

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QActionGroup, QColorDialog
from PyQt5.QtGui import QIcon, QColor

from rcc.gui.game_list import GameList
from rcc.gui.main_window import MAIN_WINDOW

from rcc import __app_name__, __version__
from rcc.models.performance_profile import PerformanceProfile
from rcc.models.rgb_brightness import RgbBrightness
from rcc.models.battery_threshold import BatteryThreshold
from rcc.services.games_service import GAME_SERVICE
from rcc.services.openrgb_service import OPEN_RGB_SERVICE
from rcc.services.platform_service import PLATFORM_SERVICE
from rcc.utils.constants import ICONS_PATH, DEV_MODE, LOG_FILE, CONFIG_FILE
from rcc.utils.beans import translator
from rcc.utils.beans import event_bus
from framework.logger import Logger
from framework.singleton import singleton


@singleton
class TrayIcon:  # pylint: disable=R0902
    """Tray icon class"""

    def __init__(self):  # pylint: disable=R0915
        self._logger = Logger()
        self._last_trigger = None

        icon = QIcon.fromTheme(os.path.join(ICONS_PATH, "icon-45x45.png"))

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(icon)
        self._tray.setToolTip(f"{__app_name__} v{__version__}")

        # Create the menu
        self._menu = QMenu()

        # Add "Battery" option (disabled)
        self._battery_action = QAction(translator.translate("battery"))
        self._battery_action.setEnabled(False)
        self._menu.addAction(self._battery_action)

        # Add "Umbral" submenu
        self._umbral_menu = QMenu("    " + translator.translate("charge.threshold"))
        self._threshold_group = QActionGroup(self._umbral_menu)
        self._threshold_group.setExclusive(True)
        self.threshold_actions: dict[BatteryThreshold, QAction] = {}
        for threshold in BatteryThreshold:
            action = QAction(f"{threshold.value}%", checkable=True)
            action.setActionGroup(self._threshold_group)
            action.setChecked(threshold == PLATFORM_SERVICE._battery_charge_limit)
            action.triggered.connect(lambda _, t=threshold: self.on_threshold_selected(t))
            self.threshold_actions[threshold] = action
            self._umbral_menu.addAction(action)
        self._menu.addMenu(self._umbral_menu)

        self._menu.addSeparator()

        # Add "AuraSync" option (disabled)
        self._aura_section = QAction("AuraSync")
        self._aura_section.setEnabled(False)
        self._menu.addAction(self._aura_section)

        # Add "Effect" submenu
        self._effect_menu = QMenu("    " + translator.translate("effect"))
        self._effect_group = QActionGroup(self._effect_menu)
        self._effect_group.setExclusive(True)
        self._effect_actions: dict[str, QAction] = {}
        for effect in OPEN_RGB_SERVICE.get_available_effects():
            action = QAction(effect, checkable=True)
            action.setActionGroup(self._effect_group)
            action.setChecked(effect == OPEN_RGB_SERVICE._effect)
            action.triggered.connect(lambda _, e=effect: self.on_effect_selected(e))
            self._effect_actions[effect] = action
            self._effect_menu.addAction(action)
        self._menu.addMenu(self._effect_menu)

        # Add "Brightness" submenu
        self._brightness_menu = QMenu("    " + translator.translate("brightness"))
        self._brightness_group = QActionGroup(self._brightness_menu)
        self._brightness_group.setExclusive(True)
        self._brightness_actions: dict[str, RgbBrightness] = {}
        for brightness in RgbBrightness:
            action = QAction(
                translator.translate(f"label.brightness.{brightness.name}"),
                checkable=True,
            )
            action.setActionGroup(self._brightness_group)
            action.setChecked(brightness == OPEN_RGB_SERVICE._brightness)
            action.triggered.connect(lambda _, b=brightness: self.on_brightness_selected(b))
            self._brightness_actions[brightness] = action
            self._brightness_menu.addAction(action)
        self._menu.addMenu(self._brightness_menu)

        # Add "Color" submenu
        self._color_menu = QMenu("    " + translator.translate("color"))

        self._color_action = QAction(OPEN_RGB_SERVICE.get_color())
        self._color_action.setEnabled(False)
        self._color_menu.addAction(self._color_action)

        self._colorpicker_action = QAction(f"{translator.translate("select.color")}...")
        self._colorpicker_action.triggered.connect(self.pick_color)
        self._color_menu.addAction(self._colorpicker_action)

        self._submenu_color = self._menu.addMenu(self._color_menu)
        self._submenu_color.setEnabled(OPEN_RGB_SERVICE.supports_color())

        self._menu.addSeparator()

        # Add "Performance" option
        self._performance_section = QAction(translator.translate("performance"))
        self._performance_section.setEnabled(False)
        self._menu.addAction(self._performance_section)

        self._profile_menu = QMenu("    " + translator.translate("profile"))
        self._performance_group = QActionGroup(self._profile_menu)
        self._performance_group.setExclusive(True)
        self._performance_actions: dict[PerformanceProfile, QAction] = {}
        for profile in reversed(PerformanceProfile):
            action = QAction(translator.translate(f"label.profile.{profile.name}"), checkable=True)
            action.setActionGroup(self._performance_group)
            action.setChecked(profile == PLATFORM_SERVICE.performance_profile)
            action.triggered.connect(lambda _, p=profile: self.on_profile_selected(p))
            self._performance_actions[profile] = action
            self._profile_menu.addAction(action)
        self._menu.addMenu(self._profile_menu)

        if GAME_SERVICE.rccdc_enabled:
            # Add "Games" option
            self._games_menu = QMenu("    " + translator.translate("games"))
            self._games_menu.setEnabled(GAME_SERVICE.steam_connected)
            self._select_profile_action = QAction(f"{translator.translate("label.game.configure")}...")
            self._select_profile_action.triggered.connect(self.on_open_game_list)
            self._games_menu.addAction(self._select_profile_action)
            self._menu.addMenu(self._games_menu)

        self._menu.addSeparator()

        if DEV_MODE:
            self._dev_section = QAction("Development")
            self._dev_section.setEnabled(False)
            self._menu.addAction(self._dev_section)

            # Add "Simulation" section
            self._simulation_menu = QMenu("    Simulation")

            self._ac_connected_action = QAction("AC connected")
            self._ac_connected_action.triggered.connect(
                lambda: PLATFORM_SERVICE._on_ac_battery_change(False, False, False)  # pylint: disable=W0212
            )
            self._simulation_menu.addAction(self._ac_connected_action)

            self._ac_disconnected_action = QAction("AC disconnected")
            self._ac_disconnected_action.triggered.connect(
                lambda: PLATFORM_SERVICE._on_ac_battery_change(True, False, False)  # pylint: disable=W0212
            )
            self._simulation_menu.addAction(self._ac_disconnected_action)

            self._simulation_menu.addSeparator()

            if GAME_SERVICE.rccdc_enabled:
                self._steam_connected_action = QAction("Steam connected")
                self._steam_connected_action.triggered.connect(lambda: event_bus.emit("SteamClient.connected"))
                self._simulation_menu.addAction(self._steam_connected_action)

                self._steam_disconnected_action = QAction("Steam disconnected")
                self._steam_disconnected_action.triggered.connect(lambda: event_bus.emit("SteamClient.disconnected"))
                self._simulation_menu.addAction(self._steam_disconnected_action)

                self._simulation_menu.addSeparator()

                self._launch_game_action = QAction("Launch game")
                self._launch_game_action.triggered.connect(
                    lambda: event_bus.emit("SteamClient.launch_game", 2891404929, "Metroid Fusion")
                )
                self._simulation_menu.addAction(self._launch_game_action)

                self._stop_game_action = QAction("Stop game")
                self._stop_game_action.triggered.connect(
                    lambda: event_bus.emit("SteamClient.stop_game", 2891404929, "Metroid Fusion")
                )
                self._simulation_menu.addAction(self._stop_game_action)

                self._menu.addMenu(self._simulation_menu)

            # Add "Open log" option
            self._open_logs_action = QAction("    Open logs")
            self._open_logs_action.triggered.connect(self.on_open_logs)
            self._menu.addAction(self._open_logs_action)

            # Add "Open settings" option
            self._open_settings_action = QAction("    Open settings")
            self._open_settings_action.triggered.connect(self.on_open_settings)
            self._menu.addAction(self._open_settings_action)

            self._menu.addSeparator()

        # Add "Open" option
        self._open_action = QAction(translator.translate("open.ui"))
        self._open_action.triggered.connect(self.on_open)
        self._menu.addAction(self._open_action)

        self._menu.addSeparator()

        # Add "Quit" option
        self._quit_action = QAction(translator.translate("close"))
        self._quit_action.triggered.connect(self.on_quit)
        self._menu.addAction(self._quit_action)

        # Set the menu on the tray icon
        self._tray.setContextMenu(self._menu)

        event_bus.on("PlatformService.battery_threshold", self.set_battery_charge_limit)
        event_bus.on("PlatformService.performance_profile", self.set_performance_profile)
        event_bus.on("OpenRgbService.aura_changed", self.set_aura_state)
        event_bus.on("GamesService.gameEvent", self.on_game_event)
        event_bus.on("GamesService.steam_connected", lambda: self.on_steam_connected_event(True))
        event_bus.on("GamesService.steam_disconnected", lambda: self.on_steam_connected_event(False))

        self._tray.activated.connect(self.on_tray_icon_activated)

    def on_game_event(self, running_games: int):
        """Handler for game events"""
        enable = running_games == 0
        self._profile_menu.setEnabled(enable)

    def on_steam_connected_event(self, connected: bool):
        """Handler for steam connection events"""
        self._games_menu.setEnabled(connected)

    def on_tray_icon_activated(self, reason):
        """Restore main window"""
        if reason == QSystemTrayIcon.Trigger:
            if self._last_trigger is not None and time.time() - self._last_trigger < 0.5:
                self.on_open()
            self._last_trigger = time.time()

    def set_battery_charge_limit(self, value: BatteryThreshold):
        """Set battery charge limit"""
        self.threshold_actions[value].setChecked(True)

    def set_performance_profile(self, value: PerformanceProfile):
        """Set performance profile"""
        self._logger.debug("Refreshing performance policy in UI")
        self._performance_actions[value].setChecked(True)

    def set_aura_state(self, value):
        """Set aura state"""
        effect, brightness, color = value

        self._effect_actions[effect].setChecked(True)
        self._brightness_actions[brightness].setChecked(True)
        if color is None:
            self._submenu_color.setEnabled(False)
        else:
            self._submenu_color.setEnabled(True)
            self._color_action.setText(color)

    def show(self):
        """Show tray"""
        self._tray.setVisible(True)

    def on_threshold_selected(self, threshold: BatteryThreshold):
        """Battery limit event handler"""
        if PLATFORM_SERVICE.battery_charge_limit != threshold:
            PLATFORM_SERVICE.set_battery_threshold(threshold)

    def on_effect_selected(self, effect: str):
        """Effect event handler"""
        if OPEN_RGB_SERVICE.effect != effect:
            OPEN_RGB_SERVICE.apply_effect(effect)

    def on_brightness_selected(self, brightness: RgbBrightness):
        """Brightness event handler"""
        if OPEN_RGB_SERVICE.brightness != brightness:
            OPEN_RGB_SERVICE.apply_brightness(brightness)

    def on_profile_selected(self, profile: PerformanceProfile):
        """Profile event handler"""
        if PLATFORM_SERVICE.performance_profile != profile:
            PLATFORM_SERVICE.set_performance_profile(profile)

    def pick_color(self):
        """Open color picker"""
        color = QColorDialog.getColor(QColor(self._color_action.text()), None, translator.translate("color.select"))
        if color.isValid():
            OPEN_RGB_SERVICE.apply_color(color.name().upper())

    def on_open_game_list(self):
        """Open game list window"""
        GameList(MAIN_WINDOW, True).show()

    @staticmethod
    def on_open():
        """Open main window"""
        MAIN_WINDOW.show()

    @staticmethod
    def on_open_logs():
        """Open log file"""
        subprocess.run(["xdg-open", LOG_FILE], check=False)

    @staticmethod
    def on_open_settings():
        """Open log file"""
        subprocess.run(["xdg-open", CONFIG_FILE], check=False)

    @staticmethod
    def on_quit():
        """Quit application"""
        event_bus.emit("stop", None)
        os.kill(os.getpid(), signal.SIGKILL)


TRAY_ICON = TrayIcon()
