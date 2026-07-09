from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QLineEdit,
    QMessageBox
)

from PyQt5.QtGui import QIcon

from controllers.firewall_controller import FirewallController


class WiFiView(QWidget):

    def __init__(self, controller: FirewallController):
        super().__init__()

        self.controller = controller

        self.init_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def init_ui(self):

        layout = QVBoxLayout(self)

        # --------------------------------------
        # Lista de redes
        # --------------------------------------

        self.wifi_list = QListWidget()

        # Duplo clique seleciona rede
        self.wifi_list.itemDoubleClicked.connect(self.select_wifi)

        layout.addWidget(self.wifi_list)

        # --------------------------------------
        # Entrada SSID
        # --------------------------------------

        self.wifi_input = QLineEdit()

        self.wifi_input.setPlaceholderText("SSID da rede Wi-Fi")

        # Enter adiciona automaticamente
        self.wifi_input.returnPressed.connect(self.add_wifi)

        layout.addWidget(self.wifi_input)

        # --------------------------------------
        # Botão escanear redes
        # --------------------------------------

        scan_button = self.create_button(
            "Procurar redes Wi-Fi",
            "resources/icons/scan.svg",
            "#3498DB",
            "#5DADE2",
            self.scan_wifi
        )

        # --------------------------------------
        # Botões principais
        # --------------------------------------

        allow_button = self.create_button(
            "Permitir Wi-Fi",
            "resources/icons/shield.svg",
            "#27AE60",
            "#2ECC71",
            self.add_wifi
        )

        block_button = self.create_button(
            "Bloquear Wi-Fi",
            "resources/icons/firewall.svg",
            "#E74C3C",
            "#C0392B",
            self.block_wifi
        )

        remove_button = self.create_button(
            "Remover Rede",
            "resources/icons/uninstall.svg",
            "#7F8C8D",
            "#95A5A6",
            self.remove_wifi
        )

        layout.addWidget(scan_button)
        layout.addWidget(allow_button)
        layout.addWidget(block_button)
        layout.addWidget(remove_button)

        # --------------------------------------

        self.refresh_wifi_networks()

    # --------------------------------------------------
    # CRIAR BOTÃO PADRÃO
    # --------------------------------------------------

    def create_button(self, text, icon_path, color, hover_color, callback):

        btn = QPushButton(text)

        btn.setIcon(QIcon(icon_path))

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-size: 14px;
                padding: 10px 8px;
                border-radius: 5px;
            }}

            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)

        btn.clicked.connect(callback)

        return btn

    # --------------------------------------------------
    # SCAN WIFI
    # --------------------------------------------------

    def scan_wifi(self):

        try:

            networks = self.controller.scan_wifi_networks()

            if not networks:

                QMessageBox.warning(
                    self,
                    "Wi-Fi",
                    "Nenhuma rede encontrada."
                )

                return

            self.wifi_list.clear()

            for ssid in networks:
                self.wifi_list.addItem(ssid)

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erro ao escanear redes",
                str(e)
            )

    # --------------------------------------------------
    # SELECIONAR REDE
    # --------------------------------------------------

    def select_wifi(self, item):

        if not item:
            return

        ssid = item.text().split(" - ")[0]

        self.wifi_input.setText(ssid)

    # --------------------------------------------------
    # PERMITIR WIFI
    # --------------------------------------------------

    def add_wifi(self):

        ssid = self.wifi_input.text().strip()

        if not ssid:

            QMessageBox.warning(
                self,
                "SSID inválido",
                "Informe o nome da rede Wi-Fi."
            )

            return

        try:

            self.controller.add_wifi_network(ssid, True)

            self.wifi_input.clear()

            self.refresh_wifi_networks()

            QMessageBox.information(
                self,
                "Wi-Fi permitida",
                f"A rede '{ssid}' foi permitida."
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erro",
                str(e)
            )

    # --------------------------------------------------
    # BLOQUEAR WIFI
    # --------------------------------------------------

    def block_wifi(self):

        ssid = self.wifi_input.text().strip()

        if not ssid:

            QMessageBox.warning(
                self,
                "SSID inválido",
                "Informe o nome da rede Wi-Fi."
            )

            return

        try:

            self.controller.add_wifi_network(ssid, False)

            self.wifi_input.clear()

            self.refresh_wifi_networks()

            QMessageBox.warning(
                self,
                "Wi-Fi bloqueada",
                f"A rede '{ssid}' foi bloqueada."
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erro",
                str(e)
            )

    # --------------------------------------------------
    # REMOVER REDE
    # --------------------------------------------------

    def remove_wifi(self):

        item = self.wifi_list.currentItem()

        if not item:

            QMessageBox.warning(
                self,
                "Seleção",
                "Selecione uma rede da lista."
            )

            return

        ssid = item.text().split(" - ")[0]

        try:

            self.controller.remove_wifi_network(ssid)

            self.refresh_wifi_networks()

            QMessageBox.information(
                self,
                "Rede removida",
                f"A rede '{ssid}' foi removida."
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erro",
                str(e)
            )

    # --------------------------------------------------
    # ATUALIZAR LISTA
    # --------------------------------------------------

    def refresh_wifi_networks(self):

        self.wifi_list.clear()

        try:

            wifi_networks = self.controller.get_wifi_networks()

            self.wifi_list.addItems(wifi_networks)

        except Exception:
            pass
