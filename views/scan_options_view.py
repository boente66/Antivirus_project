import platform
import os
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QMessageBox
from PyQt5 import QtWidgets
from views.components import FeatureCard


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
        self.main_layout.setContentsMargins(0, 4, 0, 0)
        self.main_layout.setSpacing(12)

        title = QLabel("Escolha o tipo de escaneamento")
        title.setObjectName("SectionTitle")
        self.main_layout.addWidget(title)

        # ---------------------------
        # SMART SCAN
        # ---------------------------
        smart_card = FeatureCard(
            "Verificação inteligente",
            "Analisa os locais mais importantes do sistema com equilíbrio entre velocidade e cobertura.",
            "Iniciar verificação inteligente",
            "scan",
        )
        smart_card.activated.connect(self.start_smart_scan)
        self.main_layout.addWidget(smart_card)

        # ---------------------------
        # CUSTOM SCAN
        # ---------------------------
        custom_card = FeatureCard(
            "Escaneamento personalizado",
            "Analisa o diretório padrão configurado para o usuário.",
            "Selecionar e verificar",
            "folder",
        )
        custom_card.activated.connect(self.start_custom_scan)
        self.main_layout.addWidget(custom_card)

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
