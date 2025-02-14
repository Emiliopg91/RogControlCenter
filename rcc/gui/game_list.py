from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QAbstractScrollArea,
    QHeaderView,
    QWidget,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from rcc.communications.client.websocket.steam.steam_client import SteamGameDetails, STEAM_CLIENT
from rcc.utils.constants import ICONS_PATH
from rcc.models.performance_profile import PerformanceProfile
from rcc.services.steam_service import STEAM_SERVICE
from rcc.utils.events import STEAM_SERVICE_CONNECTED
from rcc.utils.gui_utils import NoScrollComboBox
from rcc.utils.beans import EVENT_BUS, TRANSLATOR


class GameList(QDialog):
    """Window for game list"""

    INSTANCE: QDialog = None

    def __init__(self, parent: QWidget, manage_parent=False):  # pylint: disable=R0914
        super().__init__(parent)
        if GameList.INSTANCE is None:
            GameList.INSTANCE = self
            self.__parent = parent
            self.__manage_parent = manage_parent
            self.setWindowTitle(TRANSLATOR.translate("game.performance.configuration"))
            self.setFixedSize(850, 600)
            self.setWindowIcon(QIcon(f"{ICONS_PATH}/icon-45x45.png"))
            self.setAttribute(Qt.WA_DeleteOnClose)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

            # Configurar layout principal
            layout = QVBoxLayout(self)

            # Crear el área de scroll
            scroll_area = QScrollArea(self)
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # Crear un widget contenedor
            container = QWidget()
            scroll_area.setWidget(container)

            # Layout del contenedor
            container_layout = QVBoxLayout(container)

            # Crear la tabla
            game_cfg = STEAM_SERVICE.get_games()
            appids = list(game_cfg.keys())

            columns = [TRANSLATOR.translate("game.title"), TRANSLATOR.translate("profile")]
            if STEAM_SERVICE.gpu is not None:
                columns.append(TRANSLATOR.translate("used.gpu"))

            table = QTableWidget(len(appids), len(columns))
            table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
            table.setHorizontalHeaderLabels(columns)
            table.verticalHeader().setVisible(False)

            # Configurar el ancho de las columnas
            header = table.horizontalHeader()
            # Primera columna se expande
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            # Resto de columnas ajusta su tamaño al contenido
            for i in range(1, len(columns)):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.setHighlightSections(False)  # Evitar que el encabezado se resalte

            # Desactivar edición y selección en la tabla
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.setFocusPolicy(Qt.NoFocus)

            # Llenar la tabla con datos
            row = 0
            game_details = STEAM_CLIENT.get_apps_details(*appids)  # pylint: disable=W0612
            game_details = sorted(game_details, key=lambda item: item.name)
            for game in game_details:
                try:
                    col = 0
                    # Primera columna: Titulo
                    item = QTableWidgetItem(game.name)
                    item.setFlags(Qt.ItemIsEnabled)
                    table.setItem(row, col, item)
                    col += 1

                    # Segunda columna: perfil
                    profile_combo = NoScrollComboBox()  # Usar la subclase personalizada
                    for profile in reversed(PerformanceProfile):
                        profile_combo.addItem(TRANSLATOR.translate(f"label.profile.{profile.name}"), profile)

                    default_index = profile_combo.findData(
                        PerformanceProfile(game_cfg[game.appid].profile)
                    )  # Buscar el índice basado en el dato asociado
                    if default_index != -1:
                        profile_combo.setCurrentIndex(default_index)

                    # Conectar el evento currentIndexChanged al manejador
                    profile_combo.currentIndexChanged.connect(
                        lambda _, widget=profile_combo, game_id=game.appid: self.__on_profile_changed(widget, game_id)
                    )

                    table.setCellWidget(row, col, profile_combo)
                    col += 1

                    if STEAM_SERVICE.gpu is not None:
                        # Tercera columna: GPU
                        gpu_combo = NoScrollComboBox()  # Usar la subclase personalizada
                        gpu_combo.addItem(TRANSLATOR.translate("label.dgpu.auto"), False)
                        gpu_combo.addItem(TRANSLATOR.translate("label.dgpu.discrete"), True)

                        gpu_combo.setCurrentIndex(1 if game.gpu else 0)

                        gpu_combo.currentIndexChanged.connect(
                            lambda _, widget=gpu_combo, game=game: self.__on_gpu_changed(  # pylint: disable=C0301
                                widget, game
                            )
                        )
                        gpu_combo.setEnabled(game.is_steam_app)

                        table.setCellWidget(row, col, gpu_combo)
                        col += 1

                    row += 1
                except Exception as e:
                    print(f"{e}")

            # Añadir la tabla al layout del contenedor
            container_layout.addWidget(table)

            # Añadir el área de scroll al layout principal
            layout.addWidget(scroll_area)

            EVENT_BUS.on(STEAM_SERVICE_CONNECTED, self.close)

    def __on_profile_changed(self, widget, game_id):
        selected_profile = widget.currentData()  # Obtiene el objeto asociado al elemento seleccionado
        STEAM_SERVICE.set_game_profile(game_id, selected_profile)

    def __on_gpu_changed(self, widget, game: SteamGameDetails):
        enabled = widget.currentData()
        vk_opt = f"VK_ICD_FILENAMES={":".join(STEAM_SERVICE.icd_files)} "
        launch_opts = game.launch_opts
        if enabled:
            if launch_opts is None:
                launch_opts = ""
            if "%command%" not in launch_opts:
                launch_opts = f"{launch_opts.strip()} %command%"
            launch_opts = f"{vk_opt} {launch_opts.strip()}"
        else:
            launch_opts = launch_opts.replace(vk_opt, "").strip()
            if launch_opts == "%command%":
                launch_opts = ""
        STEAM_CLIENT.set_launch_options(game.appid, launch_opts)
        game.launch_opts = launch_opts

    def show(self):
        """Override default show behaviour"""
        if GameList.INSTANCE == self:
            if self.__manage_parent:
                self.__parent.show()
            super().show()
            if self.__manage_parent:
                self.__parent.hide()

    def closeEvent(self, event):  # pylint: disable=C0103
        """Override default closeEvent behaviour"""
        if GameList.INSTANCE == self:
            if self.__manage_parent:
                self.__parent.closeEvent(event)
            super().closeEvent(event)
            GameList.INSTANCE = None
