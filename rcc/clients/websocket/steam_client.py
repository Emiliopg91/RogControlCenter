from dataclasses import dataclass, field
from typing import Callable
from rcc.clients.websocket.base.abstract_websocket_client import AbstractWebsocketClient
from rcc.utils.singleton import singleton


@dataclass
class SteamGameDetails:
    """Steam game details class"""

    appid: int
    name: str
    is_steam_app: bool = field(default=True)
    launch_opts: str | None = field(default="%command%")

    @property
    def gpu(self):
        """Dedicated gpu flag"""
        return "VK_ICD_FILENAMES" in self.launch_opts


@singleton
class SteamClient(AbstractWebsocketClient):
    """Steam websocket client"""

    def __init__(self):
        super().__init__(18158)

    def on_launch_game(self, callback: Callable[[int, str], None]):
        """Handler for launch game events"""
        self.on("launch_game", callback)

    def on_stop_game(self, callback: Callable[[int, str], None]):
        """Handler for stop game events"""
        self.on("stop_game", callback)

    def get_running_games(self) -> list:
        """Retreive Steam running games. Default empty list"""
        try:
            return self._invoke("get_running_games", timeout=0.5)[0]
        except Exception:
            self._logger.debug("Could not get running games, defaulting to []")
            return []

    def get_apps_details(self, *ids: int) -> list[SteamGameDetails]:
        """Retreive Steam games details"""
        resp = self._invoke("get_apps_details", *ids)[0]
        ret: list[SteamGameDetails] = []
        for entry in resp.items():
            ret.append(
                SteamGameDetails(int(entry[0]), entry[1]["name"], entry[1]["is_steam_app"], entry[1]["launch_opts"])
            )
        return ret

    def set_launch_options(self, appid: int, launch_opts: str):
        """Set launch option for game"""
        self._invoke("set_launch_options", appid, launch_opts)


steam_client = SteamClient()
