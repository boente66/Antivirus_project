from PyQt5 import QtWidgets, QtCore

from controllers.status_controller import StatusController
from utils.icon_loader import get_icon


class StatusView(QtWidgets.QWidget):

    # ==================================================
    # INIT
    # ==================================================

    def __init__(self, parent=None, scan_controller=None):

        super().__init__(parent)

        self.scan_controller = scan_controller
        self.controller = StatusController()

        self._build_ui()
        self._connect_signals()

        # carregar status inicial
        self.refresh_status()

    # ==================================================
    # UI
    # ==================================================

    def _build_ui(self):

        layout = QtWidgets.QVBoxLayout(self)

        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # --------------------------------------------------
        # STATUS CARD
        # --------------------------------------------------

        self.card = QtWidgets.QFrame()

        self.card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #E0E0E0;
            }
        """)

        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setSpacing(10)

        # --------------------------------------------------
        # STATUS PRINCIPAL
        # --------------------------------------------------

        self.status_icon = QtWidgets.QLabel()
        self.status_icon.setAlignment(QtCore.Qt.AlignCenter)

        card_layout.addWidget(self.status_icon)

        self.status_label = QtWidgets.QLabel("Verificando status...")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)

        self.status_label.setStyleSheet(
            "font-size: 22px; font-weight: bold;"
        )

        card_layout.addWidget(self.status_label)

        # --------------------------------------------------
        # ENGINE STATUS
        # --------------------------------------------------

        self.engine_label = QtWidgets.QLabel("")
        self.engine_label.setAlignment(QtCore.Qt.AlignCenter)

        self.engine_label.setStyleSheet(
            "font-size: 14px; color: #555;"
        )

        card_layout.addWidget(self.engine_label)

        layout.addWidget(self.card)

        # --------------------------------------------------
        # BOTÃO DE SCAN
        # --------------------------------------------------

        self.scan_btn = QtWidgets.QPushButton(
            "Executar Verificação Inteligente"
        )

        self.scan_btn.setIcon(get_icon("scan"))

        self.scan_btn.setCursor(QtCore.Qt.PointingHandCursor)

        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-size: 16px;
                padding: 12px;
                border-radius: 6px;
            }

            QPushButton:hover {
                background-color: #1f8b4d;
            }

            QPushButton:pressed {
                background-color: #1a6e3d;
            }
        """)

        self.scan_btn.clicked.connect(self.run_scan)

        layout.addWidget(self.scan_btn)

        layout.addStretch()

    # ==================================================
    # SIGNALS
    # ==================================================

    def _connect_signals(self):

        self.controller.status_loaded.connect(
            self._on_status
        )

        self.controller.error.connect(
            self._on_error
        )

    # ==================================================
    # LOAD STATUS
    # ==================================================

    def refresh_status(self):

        try:

            self.status_label.setText(
                "Verificando status..."
            )

            self.engine_label.setText("")

            self.status_icon.setPixmap(
                get_icon("loading").pixmap(48, 48)
                if get_icon("loading") else QtCore.QSize()
            )

            self.controller.load_status()

        except Exception as e:

            self._on_error(str(e))

    # ==================================================
    # CALLBACKS
    # ==================================================

    def _on_status(self, data):

        try:

            protection = data.get("protection")
            engine = data.get("engine", "Desconhecido")

            if protection == "active":

                self.status_label.setText(
                    "✔ Este computador está protegido"
                )

                self.status_label.setStyleSheet(
                    "font-size: 22px; font-weight: bold; color: #27AE60;"
                )

                self.status_icon.setPixmap(
                    get_icon("shield").pixmap(48, 48)
                )

            else:

                self.status_label.setText(
                    "⚠ Proteção inativa"
                )

                self.status_label.setStyleSheet(
                    "font-size: 22px; font-weight: bold; color: #E74C3C;"
                )

                self.status_icon.setPixmap(
                    get_icon("warning").pixmap(48, 48)
                )

            self.engine_label.setText(
                f"ClamAV: {engine}"
            )

        except Exception as e:

            self._on_error(str(e))

    # --------------------------------------------------

    def _on_error(self, msg):

        QtWidgets.QMessageBox.critical(
            self,
            "Erro",
            str(msg)
        )

    # ==================================================
    # ACTIONS
    # ==================================================

    def run_scan(self):

        if not self.scan_controller:

            QtWidgets.QMessageBox.warning(
                self,
                "Verificação",
                "Controlador de scan não disponível."
            )

            return

        try:

            self.scan_btn.setEnabled(False)

            self.scan_controller.start_smart_scan()

            QtCore.QTimer.singleShot(
                2000,
                lambda: self.scan_btn.setEnabled(True)
            )

        except Exception as e:

            self.scan_btn.setEnabled(True)

            QtWidgets.QMessageBox.critical(
                self,
                "Erro ao iniciar verificação",
                str(e)
            )