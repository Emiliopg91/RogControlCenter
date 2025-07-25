import os
from dataclasses import dataclass
from threading import Thread

from framework.logger import Logger
from rcc.communications.client.cmd.linux.mangohud_client import MANGO_HUD_CLIENT
from rcc.communications.client.cmd.linux.systemctl_client import SYSTEM_CTL_CLIENT
from rcc.communications.client.tcp.openrgb.effects.gaming import GAMING_EFFECT
from rcc.communications.client.websocket.steam.steam_client import STEAM_CLIENT
from rcc.models.gpu_brand import GpuBrand
from rcc.models.mangohud_level import MangoHudLevel
from rcc.models.ntsync_option import NtSyncOption
from rcc.models.performance_profile import PerformanceProfile
from rcc.models.settings import GameEntry
from rcc.services.hardware_service import HARDWARE_SERVICE
from rcc.services.profile_service import PROFILE_SERVICE
from rcc.services.rgb_service import RGB_SERVICE
from rcc.utils.beans import EVENT_BUS
from rcc.utils.configuration import CONFIGURATION
from rcc.utils.constants import RCCDC_ASSET_PATH, USER_PLUGIN_FOLDER, USER_SCRIPTS_FOLDER
from rcc.utils.events import STEAM_SERVICE_CONNECTED, STEAM_SERVICE_DISCONNECTED, STEAM_SERVICE_GAME_EVENT
from rcc.utils.shell import SHELL


@dataclass
class RunningGameModel:
    """Running game class"""

    id: int
    name: str


class SteamService:
    """Steam service"""

    WRAPER_PATH = os.path.join(USER_SCRIPTS_FOLDER, "runGame.py")

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

            HARDWARE_SERVICE.set_panel_overdrive(True)
            self.__set_profile_for_games()
            RGB_SERVICE.apply_effect(GAMING_EFFECT.name, True)
            self._logger.rem_tab()

            if CONFIGURATION.games.get(gid) is None:
                CONFIGURATION.games[gid] = GameEntry(name, None, MangoHudLevel.NO_DISPLAY)
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

    def get_metrics_level(self, app_id) -> MangoHudLevel:
        """Get level for game"""
        game = CONFIGURATION.games.get(app_id)
        return (
            MangoHudLevel(game.metrics_level) if game and game.metrics_level is not None else MangoHudLevel.NO_DISPLAY
        )

    def set_metrics_level(self, metric_level: MangoHudLevel, app_id, launch_options) -> MangoHudLevel:
        """Set level for game launch option"""
        gpu_brand = self.get_prefered_gpu(app_id)
        ntsync_level = self.get_ntsync_level(app_id)
        environment = self.get_environment(app_id)
        params = self.get_parameters(app_id)
        return self.__set_launch_options(
            app_id, launch_options, gpu_brand, metric_level, ntsync_level, environment, params
        )

    def get_ntsync_level(self, app_id) -> NtSyncOption:
        """Get level for game"""
        game = CONFIGURATION.games.get(app_id)
        return NtSyncOption(game.ntsync) if game and game.ntsync is not None else NtSyncOption.ON

    def set_ntsync_level(self, ntsync_level: NtSyncOption, app_id, launch_options) -> MangoHudLevel:
        """Set level for game launch option"""
        gpu_brand = self.get_prefered_gpu(app_id)
        metric_level = self.get_metrics_level(app_id)
        environment = self.get_environment(app_id)
        params = self.get_parameters(app_id)
        return self.__set_launch_options(
            app_id, launch_options, gpu_brand, metric_level, ntsync_level, environment, params
        )

    def get_prefered_gpu(self, app_id) -> GpuBrand | None:
        """Get GPU from game launch option"""
        game = CONFIGURATION.games.get(app_id)
        return GpuBrand(game.gpu) if game and game.gpu is not None else None

    def set_prefered_gpu(self, gpu_brand: GpuBrand, app_id, launch_options) -> MangoHudLevel:
        """Set gpu for game launch option"""
        metric_level = self.get_metrics_level(app_id)
        ntsync_level = self.get_ntsync_level(app_id)
        environment = self.get_environment(app_id)
        params = self.get_parameters(app_id)
        return self.__set_launch_options(
            app_id, launch_options, gpu_brand, metric_level, ntsync_level, environment, params
        )

    def get_environment(self, app_id) -> str:
        """Get defined env for game"""
        game = CONFIGURATION.games.get(app_id)
        return game.env if game.env is not None else ""

    def set_environment(self, env: str, app_id, launch_options) -> MangoHudLevel:
        """Set gpu for game launch option"""
        metric_level = self.get_metrics_level(app_id)
        ntsync_level = self.get_ntsync_level(app_id)
        gpu_brand = self.get_prefered_gpu(app_id)
        params = self.get_parameters(app_id)
        return self.__set_launch_options(
            app_id, launch_options, gpu_brand, metric_level, ntsync_level, env.strip(), params
        )

    def get_parameters(self, app_id) -> str:
        """Get defined params for game"""
        game = CONFIGURATION.games.get(app_id)
        return game.args if game.args is not None else ""

    def set_parameters(self, param: str, app_id, launch_options) -> MangoHudLevel:
        """Set gpu for game launch option"""
        metric_level = self.get_metrics_level(app_id)
        ntsync_level = self.get_ntsync_level(app_id)
        gpu_brand = self.get_prefered_gpu(app_id)
        environment = self.get_environment(app_id)
        return self.__set_launch_options(
            app_id, launch_options, gpu_brand, metric_level, ntsync_level, environment, param.strip()
        )

    def __set_launch_options(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        app_id: int,
        launch_options: str,
        gpu_brand: GpuBrand,
        metric_level: MangoHudLevel,
        ntsync_level: NtSyncOption,
        environment: str,
        params: str,
    ):
        launch_opts = launch_options

        if gpu_brand is None and metric_level == MangoHudLevel.NO_DISPLAY and ntsync_level == NtSyncOption.OFF:
            if self.WRAPER_PATH in launch_opts:
                launch_opts = launch_opts.replace(self.WRAPER_PATH, "").strip()

            if launch_opts.startswith("%command%"):
                launch_opts = launch_opts.replace("%command%", "").strip()

        else:
            if self.WRAPER_PATH not in launch_opts:
                if launch_opts is None or launch_opts == "":
                    launch_opts = "%command%"
                elif "%command%" not in launch_opts:
                    launch_opts = "%command% " + launch_opts

                launch_opts = launch_opts.replace("%command%", f"{self.WRAPER_PATH} %command%")

        game = CONFIGURATION.games.get(app_id)
        game.gpu = gpu_brand.value if gpu_brand is not None else None
        game.metrics_level = metric_level.value if metric_level is not None else MangoHudLevel.NO_DISPLAY.value
        game.ntsync = ntsync_level.value if ntsync_level is not None else NtSyncOption.ON.value
        game.env = environment
        game.args = params
        CONFIGURATION.save_config()

        STEAM_CLIENT.set_launch_options(app_id, launch_opts)

        return launch_opts

    def get_run_configuration(self, app_id):
        "Get environment and wrappers for app_id"
        environment = {}
        wrappers = []
        params = ""

        game = CONFIGURATION.games.get(app_id)
        if game is not None:
            environment["SteamDeck"] = "0"

            if game.ntsync == NtSyncOption.OFF.value:
                environment["PROTON_USE_NTSYNC"] = "0"

            if game.gpu is not None:
                environment.update(HARDWARE_SERVICE.get_gpu_selector_env(GpuBrand(game.gpu)))

            if game.metrics_level != MangoHudLevel.NO_DISPLAY:
                environment["MANGOHUD"] = "1"
                environment["MANGOHUD_CONFIG"] = f"preset={game.metrics_level}"
                wrappers.append("mangohud")

            if game.env is not None and len(game.env.strip()):
                env = game.env.strip()
                parts = env.split(" ")
                for part in parts:
                    env_parts = part.split("=")
                    environment[env_parts[0]] = env_parts[1]

            if game.args is not None:
                params = game.args.strip()

        self._logger.info(f"Config for {game.name}:")
        self._logger.info(f"  Environment: {environment}")
        self._logger.info(f"  Wrappers: {wrappers}")

        return environment, wrappers, params


STEAM_SERVICE = SteamService()
