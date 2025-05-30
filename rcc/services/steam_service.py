import os
import re
from dataclasses import dataclass
from threading import Thread

from framework.logger import Logger
from rcc.communications.client.cmd.linux.mangohud_client import MANGO_HUD_CLIENT
from rcc.communications.client.cmd.linux.systemctl_client import SYSTEM_CTL_CLIENT
from rcc.communications.client.tcp.openrgb.effects.gaming import GAMING_EFFECT
from rcc.communications.client.websocket.steam.steam_client import STEAM_CLIENT
from rcc.models.gpu_brand import GpuBrand
from rcc.models.mangohud_level import MangoHudLevel
from rcc.models.performance_profile import PerformanceProfile
from rcc.models.settings import GameEntry
from rcc.services.hardware_service import HARDWARE_SERVICE
from rcc.services.profile_service import PROFILE_SERVICE
from rcc.services.rgb_service import RGB_SERVICE
from rcc.utils.beans import EVENT_BUS
from rcc.utils.configuration import CONFIGURATION
from rcc.utils.constants import RCCDC_ASSET_PATH, USER_PLUGIN_FOLDER
from rcc.utils.events import STEAM_SERVICE_CONNECTED, STEAM_SERVICE_DISCONNECTED, STEAM_SERVICE_GAME_EVENT
from rcc.utils.shell import SHELL


@dataclass
class RunningGameModel:
    """Running game class"""

    id: int
    name: str


class SteamService:
    """Steam service"""

    DECKY_SERVICE_PATH = os.path.expanduser(os.path.join("~", "homebrew", "services", "PluginLoader"))
    PLUGINS_FOLDER = os.path.expanduser(os.path.join("~", "homebrew", "plugins"))
    RCCDC_PATH = os.path.join(PLUGINS_FOLDER, "RCCDeckyCompanion")

    def __init__(self):
        self._logger = Logger()
        self._logger.info("Initializing SteamService")
        self._logger.add_tab()
        self._rccdc_enabled = False
        self.__running_games: dict[int, str] = {}
        self.__steam_connnected = STEAM_CLIENT.connected

        STEAM_CLIENT.on_connected(self.__on_steam_connected)
        STEAM_CLIENT.on_disconnected(self.__on_steam_disconnected)
        STEAM_CLIENT.on_launch_game(self.__launch_game)
        STEAM_CLIENT.on_stop_game(self.__stop_game)

        if STEAM_CLIENT.connected:
            self.__on_steam_connected(True)

        self._logger.rem_tab()

    def __on_steam_connected(self, on_boot=False):
        self.__running_games = {}
        self._logger.info("SteamClient connected")
        self._logger.add_tab()
        if not on_boot:
            self.__set_profile_for_games(True)
        self._logger.rem_tab()
        self.__steam_connnected = True
        EVENT_BUS.emit(STEAM_SERVICE_CONNECTED)

    def __on_steam_disconnected(self):
        self._logger.info("SteamClient disconnected")
        self.__steam_connnected = False
        if self.running_games:
            PROFILE_SERVICE.restore_profile()
        EVENT_BUS.emit(STEAM_SERVICE_DISCONNECTED)

    @property
    def steam_connected(self):
        """Flag for steam connection"""
        return self.__steam_connnected

    @property
    def metrics_enabled(self):
        """Flag metrics availability"""
        return MANGO_HUD_CLIENT.available

    def get_games(self) -> dict[int, str]:
        """Get games and setting"""
        return CONFIGURATION.games

    def __set_profile_for_games(self, on_connect=False):
        if len(self.__running_games) > 0:
            PROFILE_SERVICE.set_performance_profile(PerformanceProfile.PERFORMANCE, True, True)
        elif not on_connect:
            PROFILE_SERVICE.restore_profile()

        EVENT_BUS.emit(STEAM_SERVICE_GAME_EVENT, len(self.__running_games))

    def __launch_game(self, gid: int, name: str, pid: int):
        self._logger.info(f"Launched {name} with PID {pid}")
        if gid not in self.running_games:
            self.__running_games[gid] = name
            self._logger.add_tab()

            HARDWARE_SERVICE.apply_proccess_optimizations(pid)
            HARDWARE_SERVICE.set_panel_overdrive(True)
            self.__set_profile_for_games()
            RGB_SERVICE.apply_effect(GAMING_EFFECT.name, True)
            self._logger.rem_tab()

            if CONFIGURATION.games.get(gid) is None:
                CONFIGURATION.games[gid] = GameEntry(name)
                CONFIGURATION.save_config()

    def __stop_game(self, gid: int, name: str):
        self._logger.info(f"Stopped {name}")
        if gid in self.running_games:
            del self.running_games[gid]
        if len(self.running_games.keys()) == 0:
            RGB_SERVICE.restore_effect()
        self._logger.add_tab()
        HARDWARE_SERVICE.set_panel_overdrive(len(self.running_games) > 0)
        self.__set_profile_for_games()
        self._logger.rem_tab()

    @property
    def running_games(self):
        """Get list of running games"""
        return self.__running_games

    @property
    def rccdc_enabled(self):
        """If plugin is enabled"""
        return self._rccdc_enabled

    def install_rccdc(self):
        """Install RCCDeckyCompanion plugin"""

        if os.path.exists(self.DECKY_SERVICE_PATH):
            if not os.path.exists(self.RCCDC_PATH):
                self._logger.info("Installing plugin for first time")
                self.__copy_plugin(RCCDC_ASSET_PATH, os.path.join(self.PLUGINS_FOLDER, "RCCDeckyCompanion"), False)
            else:
                if os.path.getmtime(self.RCCDC_PATH) < os.path.getmtime(RCCDC_ASSET_PATH):
                    self._logger.info("Updating Decky plugin")
                    self.__copy_plugin(RCCDC_ASSET_PATH, os.path.join(self.PLUGINS_FOLDER, "RCCDeckyCompanion"), True)
                else:
                    self._logger.debug("Plugin up to date")
            self._rccdc_enabled = True
        else:
            self._logger.warning("No Decky installation found, skipping plugin installation")
            self._rccdc_enabled = False

    def __copy_plugin(self, src: str, dst: str, is_update: bool):
        SHELL.run_command(f"cp -R {src} {USER_PLUGIN_FOLDER}", False)
        if is_update:
            SHELL.run_command(f"rm -R {dst}", True)
        SHELL.run_command(f"cp -R {os.path.join(USER_PLUGIN_FOLDER, 'RCCDeckyCompanion')} {dst}", True)
        Thread(target=lambda: SYSTEM_CTL_CLIENT.restart_service("plugin_loader")).start()

    def get_metrics_level(self, launch_options) -> MangoHudLevel:
        """Get level from game launch option"""
        match = re.search(r"(?<=preset=)(-?\d+)", launch_options)
        if match:
            return MangoHudLevel(int(match.group(0)))

        return MangoHudLevel.NO_DISPLAY

    def set_metrics_level(self, metric_level: MangoHudLevel, app_id, launch_options) -> MangoHudLevel:
        """Set level for game launch option"""
        gpu_brand = self.get_prefered_gpu(launch_options)
        return self.__set_launch_options(app_id, launch_options, gpu_brand, metric_level)

    def get_prefered_gpu(self, launch_options) -> GpuBrand | None:
        """Get GPU from game launch option"""
        for gpu in HARDWARE_SERVICE.gpus:
            if f"RCC_GPU={gpu.value} " in launch_options:
                return gpu

        return None

    def set_prefered_gpu(self, gpu_brand: GpuBrand, app_id, launch_options) -> MangoHudLevel:
        """Set gpu for game launch option"""
        metric_level = self.get_metrics_level(launch_options)
        return self.__set_launch_options(app_id, launch_options, gpu_brand, metric_level)

    def __set_launch_options(self, app_id: int, launch_options: str, gpu_brand: GpuBrand, metric_level: MangoHudLevel):
        launch_opts = launch_options

        if launch_opts is None or launch_opts == "":
            launch_opts = "%command%"
        elif "%command%" not in launch_opts:
            launch_opts = "%command% " + launch_opts

        launch_opts = re.sub(r"SteamDeck=0 ", "", launch_opts).strip()
        launch_opts = re.sub(r"MANGOHUD=.* MANGOHUD_CONFIG=preset=[^ ]+ mangohud ", "", launch_opts).strip()
        prev_gpu = self.get_prefered_gpu(launch_options)
        if prev_gpu is not None:
            for part in HARDWARE_SERVICE.get_gpu_selector_env(prev_gpu).split(" "):
                launch_opts = re.sub(rf"{part} ", "", launch_opts).strip()

        if metric_level > 0:
            launch_opts = launch_opts.replace(
                "%command%", f"MANGOHUD=1 MANGOHUD_CONFIG=preset={metric_level.value} mangohud %command%"
            )

        if gpu_brand is not None:
            launch_opts = HARDWARE_SERVICE.get_gpu_selector_env(gpu_brand) + " " + launch_opts

        launch_opts = "SteamDeck=0 " + launch_opts.strip()

        STEAM_CLIENT.set_launch_options(app_id, launch_opts)

        return launch_opts


STEAM_SERVICE = SteamService()
