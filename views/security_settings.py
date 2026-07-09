from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from controllers.security_controller import SecurityController
from utils.icon_loader import get_icon


class SecuritySettingsView(QtWidgets.QWidget):

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):
        super().__init__()

        self.controller = SecurityController(self)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.tabs = QtWidgets.QTabWidget()

        layout.addWidget(self.tabs)

        self.create_clamav_tab()
        self.create_ransomware_tab()

    # =====================================================
    # CLAMAV TAB
    # =====================================================

    def create_clamav_tab(self):

        tab = QtWidgets.QWidget()

        vbox = QtWidgets.QVBoxLayout(tab)
        vbox.setSpacing(10)

        # -------------------------
        # Tipo conexão
        # -------------------------

        connection_label = QtWidgets.QLabel("Tipo de conexão:")

        self.connection_combo = QtWidgets.QComboBox()
        self.connection_combo.addItems(["Local", "Servidor"])

        vbox.addWidget(connection_label)
        vbox.addWidget(self.connection_combo)

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

        vbox.addWidget(self.server_frame)

        self.server_frame.hide()

        self.connection_combo.currentIndexChanged.connect(
            self._toggle_server_fields
        )

        # -------------------------
        # BOTÕES
        # -------------------------

        btn_layout = QtWidgets.QHBoxLayout()

        self.connect_btn = QtWidgets.QPushButton("Conectar")
        self.connect_btn.setIcon(get_icon("shield"))
        self.connect_btn.clicked.connect(self.on_connect)

        self.disconnect_btn = QtWidgets.QPushButton("Desconectar")
        self.disconnect_btn.setIcon(get_icon("shield_off"))
        self.disconnect_btn.clicked.connect(self.on_disconnect)

        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)

        vbox.addLayout(btn_layout)

        # -------------------------
        # STATUS
        # -------------------------

        self.status_label = QtWidgets.QLabel("Status: desconhecido")
        vbox.addWidget(self.status_label)

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

        # -------------------------
        # DIRETÓRIO
        # -------------------------

        self.directory_label = QtWidgets.QLabel(
            "Nenhum diretório selecionado."
        )

        vbox.addWidget(self.directory_label)

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

        vbox.addWidget(select_path_btn)
        vbox.addWidget(self.toggle_protection_button)

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
