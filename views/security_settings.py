from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from controllers.security_controller import SecurityController
from utils.icon_loader import get_icon
from views.components import CardFrame


class SecuritySettingsView(QtWidgets.QWidget):

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, scan_controller=None):
        super().__init__()

        self.controller = SecurityController(self)
        self.scan_controller = scan_controller
        self.selected_directory = None

        self.init_ui()

    # =====================================================
    # UI Helpers (Chamadas pelo Controller)
    # =====================================================

    def update_status(self, text):

        self.status_label.setText(f"Status: {text}")

        if text == "Ativo":

            self.status_label.setStyleSheet(
                "color: #27AE60; font-weight: bold;"
            )

            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)

        elif text == "Desativado":

            self.status_label.setStyleSheet(
                "color: #E74C3C; font-weight: bold;"
            )

            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)

        else:

            self.status_label.setStyleSheet(
                "color: orange; font-weight: bold;"
            )

    # -----------------------------------------------------

    def show_error(self, message):
        QMessageBox.critical(self, "Erro", message)

    def show_info(self, message):
        QMessageBox.information(self, "Informação", message)

    def show_warning(self, message):
        QMessageBox.warning(self, "Aviso", message)

    def show_notification(self, message):
        QMessageBox.warning(self, "Alerta de Segurança", message)

    def update_toggle_button(self, text):
        self.toggle_protection_button.setText(text)

    # =====================================================
    # UI Layout
    # =====================================================

    def init_ui(self):

        self.setWindowTitle("Configurações de Segurança")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        self.tabs = QtWidgets.QTabWidget()

        layout.addWidget(self.tabs)

        self.create_clamav_tab()
        self.create_scan_tab()
        self.create_ransomware_tab()

    def create_scan_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(12, 16, 12, 12)
        card = CardFrame()
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        title = QtWidgets.QLabel("Avisos antes do escaneamento")
        title.setObjectName("SectionTitle")
        description = QtWidgets.QLabel(
            "Defina quando o aplicativo deve alertar sobre programas abertos."
        )
        description.setProperty("muted", True)
        description.setWordWrap(True)
        card_layout.addWidget(title)
        card_layout.addWidget(description)

        self.browser_warning_checkbox = QtWidgets.QCheckBox(
            "Avisar quando houver navegadores abertos antes do "
            "escaneamento completo."
        )
        self.browser_warning_checkbox.setToolTip(
            "Também controla o aviso antes de escaneamentos personalizados."
        )

        if self.scan_controller is None:
            self.browser_warning_checkbox.setEnabled(False)
        else:
            self.browser_warning_checkbox.setChecked(
                self.scan_controller.browser_warning_enabled()
            )
            self.browser_warning_checkbox.toggled.connect(
                self.scan_controller.set_browser_warning_enabled
            )
            self.scan_controller.browser_warning_preference_changed.connect(
                self._update_browser_warning_checkbox
            )

        card_layout.addWidget(self.browser_warning_checkbox)
        layout.addWidget(card)
        layout.addStretch()
        self.tabs.addTab(tab, get_icon("scan"), "Escaneamento")

    def _update_browser_warning_checkbox(self, enabled):
        self.browser_warning_checkbox.blockSignals(True)
        self.browser_warning_checkbox.setChecked(bool(enabled))
        self.browser_warning_checkbox.blockSignals(False)

    # =====================================================
    # CLAMAV TAB
    # =====================================================

    def create_clamav_tab(self):

        tab = QtWidgets.QWidget()

        vbox = QtWidgets.QVBoxLayout(tab)
        vbox.setSpacing(10)
        vbox.setContentsMargins(12, 16, 12, 12)

        connection_card = CardFrame()
        connection_layout = QtWidgets.QVBoxLayout(connection_card)
        connection_layout.setContentsMargins(18, 16, 18, 18)
        connection_title = QtWidgets.QLabel("Conexão ClamAV")
        connection_title.setObjectName("SectionTitle")
        connection_description = QtWidgets.QLabel(
            "Configure a conexão com o mecanismo responsável pela detecção de ameaças."
        )
        connection_description.setProperty("muted", True)
        connection_description.setWordWrap(True)
        connection_layout.addWidget(connection_title)
        connection_layout.addWidget(connection_description)

        # -------------------------
        # Tipo conexão
        # -------------------------

        connection_label = QtWidgets.QLabel("Tipo de conexão:")

        self.connection_combo = QtWidgets.QComboBox()
        self.connection_combo.addItems(["Local", "Servidor"])

        connection_layout.addWidget(connection_label)
        connection_layout.addWidget(self.connection_combo)

        # -------------------------
        # Server frame
        # -------------------------

        self.server_frame = QtWidgets.QFrame()

        s_layout = QtWidgets.QVBoxLayout(self.server_frame)

        self.server_address = QtWidgets.QLineEdit()
        self.server_address.setPlaceholderText("Endereço do servidor")

        self.server_port = QtWidgets.QLineEdit()
        self.server_port.setPlaceholderText("Porta")

        s_layout.addWidget(self.server_address)
        s_layout.addWidget(self.server_port)

        connection_layout.addWidget(self.server_frame)

        self.server_frame.hide()

        self.connection_combo.currentIndexChanged.connect(
            self._toggle_server_fields
        )

        # -------------------------
        # BOTÕES
        # -------------------------

        btn_layout = QtWidgets.QHBoxLayout()

        self.connect_btn = QtWidgets.QPushButton("Conectar")
        self.connect_btn.setProperty("role", "primary")
        self.connect_btn.setIcon(get_icon("shield"))
        self.connect_btn.clicked.connect(self.on_connect)

        self.disconnect_btn = QtWidgets.QPushButton("Desconectar")
        self.disconnect_btn.setProperty("role", "secondary")
        self.disconnect_btn.setIcon(get_icon("shield_off"))
        self.disconnect_btn.clicked.connect(self.on_disconnect)

        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)

        connection_layout.addLayout(btn_layout)

        # -------------------------
        # STATUS
        # -------------------------

        self.status_label = QtWidgets.QLabel("Status: desconhecido")
        connection_layout.addWidget(self.status_label)
        vbox.addWidget(connection_card)

        vbox.addStretch()

        # -------------------------
        # ADICIONAR ABA
        # -------------------------

        self.tabs.addTab(tab, get_icon("shield"), "ClamAV")

        # Atualizar status real
        self.controller.refresh_clamav_status()

    # ----------------------------------------------------------

    def _toggle_server_fields(self):

        if self.connection_combo.currentText() == "Servidor":
            self.server_frame.show()
        else:
            self.server_frame.hide()

    # ----------------------------------------------------------

    def on_connect(self):

        mode = self.connection_combo.currentText()

        if mode == "Local":

            self.controller.connect_clamav("Local")

        else:

            addr = self.server_address.text().strip()
            port = self.server_port.text().strip()

            if not addr or not port:

                QMessageBox.warning(
                    self,
                    "Dados incompletos",
                    "Informe o endereço e a porta do servidor."
                )
                return

            self.controller.connect_clamav(
                "Servidor",
                addr,
                port
            )

        self.controller.refresh_clamav_status()

    # ----------------------------------------------------------

    def on_disconnect(self):

        self.controller.disconnect_clamav()
        self.controller.refresh_clamav_status()

    # =====================================================
    # RANSOMWARE TAB
    # =====================================================

    def create_ransomware_tab(self):

        tab = QtWidgets.QWidget()

        vbox = QtWidgets.QVBoxLayout(tab)
        vbox.setSpacing(10)
        vbox.setContentsMargins(12, 16, 12, 12)
        card = CardFrame()
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        title = QtWidgets.QLabel("Proteção contra ransomware")
        title.setObjectName("SectionTitle")
        description = QtWidgets.QLabel(
            "Selecione um diretório para controlar a proteção já disponível no aplicativo."
        )
        description.setProperty("muted", True)
        description.setWordWrap(True)
        card_layout.addWidget(title)
        card_layout.addWidget(description)

        # -------------------------
        # DIRETÓRIO
        # -------------------------

        self.directory_label = QtWidgets.QLabel(
            "Nenhum diretório selecionado."
        )

        card_layout.addWidget(self.directory_label)

        # -------------------------
        # BOTÃO SELECIONAR PASTA
        # -------------------------

        select_path_btn = QtWidgets.QPushButton(
            "Selecionar Diretório"
        )

        select_path_btn.setIcon(get_icon("folder"))

        select_path_btn.clicked.connect(
            self.on_select_directory
        )

        # -------------------------
        # BOTÃO ATIVAR PROTEÇÃO
        # -------------------------

        self.toggle_protection_button = QtWidgets.QPushButton(
            "Ativar Proteção"
        )

        self.toggle_protection_button.setIcon(
            get_icon("shield_lock")
        )

        self.toggle_protection_button.clicked.connect(
            self.on_toggle_ransomware
        )

        select_path_btn.setProperty("role", "secondary")
        self.toggle_protection_button.setProperty("role", "primary")
        card_layout.addWidget(select_path_btn)
        card_layout.addWidget(self.toggle_protection_button)
        vbox.addWidget(card)

        vbox.addStretch()

        # -------------------------
        # ADICIONAR ABA
        # -------------------------

        self.tabs.addTab(
            tab,
            get_icon("shield_lock"),
            "Proteção Ransomware"
        )

    # ----------------------------------------------------------

    def on_select_directory(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecione o Diretório"
        )

        if folder:

            self.selected_directory = folder

            self.directory_label.setText(
                f"Diretório protegido: {folder}"
            )

    # ----------------------------------------------------------

    def on_toggle_ransomware(self):

        if not self.selected_directory:

            QMessageBox.warning(
                self,
                "Proteção",
                "Selecione um diretório primeiro."
            )

            return

        self.controller.toggle_ransomware(
            self.selected_directory
        )
