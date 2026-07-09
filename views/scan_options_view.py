import platform
import os
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QMessageBox
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont


class CustomScanView(QWidget):
    """
    View responsável apenas por:
    - Exibir opções de escaneamento
    - Coletar escolha do usuário
    - Disparar o ScanController

    NÃO cria ScanView
    NÃO chama serviços
    """

    def __init__(self, scan_controller, parent=None):
        super().__init__(parent)
        self.scan_controller = scan_controller
        self.parent_view = parent

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self._build_ui()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        self.setWindowTitle("Escaneamento Personalizado")
        self.setMinimumSize(500, 300)

        title = QLabel("Escolha o tipo de escaneamento")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #2C3E50; padding: 12px;")
        self.main_layout.addWidget(title)

        # ---------------------------
        # SMART SCAN
        # ---------------------------
        smart_btn = QPushButton("Verificação Inteligente (Recomendado)")
        smart_btn.setStyleSheet(self._btn_style("#27AE60", "#1E8449"))
        smart_btn.clicked.connect(self.start_smart_scan)
        self.main_layout.addWidget(smart_btn)

        # ---------------------------
        # CUSTOM SCAN
        # ---------------------------
        custom_btn = QPushButton("Escaneamento Personalizado")
        custom_btn.setStyleSheet(self._btn_style("#3498DB", "#2E86C1"))
        custom_btn.clicked.connect(self.start_custom_scan)
        self.main_layout.addWidget(custom_btn)

        self.main_layout.addStretch()

    # ============================================================
    # AÇÕES
    # ============================================================

    def start_smart_scan(self):
        """
        Dispara o Smart Scan.
        Controller decide alvos, histórico e UI.
        """
        try:
            self.scan_controller.start_smart_scan()
            self._close_self()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def start_custom_scan(self):
        """
        Dispara scan a partir de um diretório base.
        """
        base_path = self._get_default_directory()

        if not os.path.exists(base_path):
            QMessageBox.critical(
                self,
                "Erro",
                "Diretório inicial não encontrado."
            )
            return

        try:
            self.scan_controller.start_custom_scan(base_path)
            self._close_self()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    # ============================================================
    # UTILITÁRIOS
    # ============================================================

    def _get_default_directory(self):
        if platform.system() == "Linux":
            return os.path.expanduser("~")
        elif platform.system() == "Windows":
            user = os.getenv("USERNAME")
            return f"C:\\Users\\{user}"
        return "/"

    def _close_self(self):
        """Remove esta view após iniciar o scan"""
        self.setParent(None)
        self.deleteLater()

    def _btn_style(self, color, hover):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-size: 14px;
                padding: 10px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """