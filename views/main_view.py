from PyQt5 import QtWidgets, QtCore

from controllers.scan_controller import ScanController
from controllers.cleaner_controller import CleanerController
from controllers.quarantine_controller import QuarantineController

from views.status_view import StatusView
from views.firewall_view import FirewallView
from views.historic_view import HistoricView
from views.scan_options_view import CustomScanView
from views.scan_view import ScanView
from views.security_settings import SecuritySettingsView
from views.cleaner_view import CleanerView
from views.uninstaller_view import UninstallerView
from views.disk_usage_view import DiskUsageView
from views.quarantine_view import QuarantineView

from utils.icon_loader import get_icon


class MainView(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Antivírus")
        self.setFixedSize(800, 600)

        # --------------------------------------------------
        # Controllers
        # --------------------------------------------------

        self.quarantine_controller = QuarantineController()
        self.scan_controller = ScanController(
            parent=self,
            quarantine_service=self.quarantine_controller.service
        )
        self.cleaner_controller = CleanerController()

        # --------------------------------------------------
        # Layout principal
        # --------------------------------------------------

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QtWidgets.QHBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # --------------------------------------------------
        # MENU LATERAL
        # --------------------------------------------------

        self._build_sidebar()

        # --------------------------------------------------
        # ÁREA DE CONTEÚDO
        # --------------------------------------------------

        self._build_content_area()

        # --------------------------------------------------
        # Páginas
        # --------------------------------------------------

        self._create_pages()

        self.scan_controller.scan_started.connect(self.show_scan_view)

        self.show_status()

    # ==================================================
    # SIDEBAR
    # ==================================================

    def _build_sidebar(self):

        self.menu_frame = QtWidgets.QFrame()
        self.menu_frame.setFixedWidth(180)

        self.menu_frame.setStyleSheet("""
            background-color: #2C3E50;
            border-right: 2px solid #34495E;
        """)

        self.layout.addWidget(self.menu_frame)

        self.menu_layout = QtWidgets.QVBoxLayout(self.menu_frame)
        self.menu_layout.setAlignment(QtCore.Qt.AlignTop)

        self._create_menu_button("Status", "status", self.show_status)
        self._create_menu_button("Proteção", "shield", self.show_protection)
        self._create_menu_button("Otimização", "cleaner", self.show_optimization)
        self._create_menu_button("Configurações", "settings", self.show_settings)

        self.menu_layout.addStretch()

    # --------------------------------------------------

    def _create_menu_button(self, text, icon, callback):

        btn = QtWidgets.QPushButton(text)

        btn.setIcon(get_icon(icon))
        btn.setIconSize(QtCore.QSize(18, 18))

        btn.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: white;
                font-size: 14px;
                border: none;
                padding: 10px;
                text-align: left;
            }

            QPushButton:hover {
                background-color: #34495E;
            }
        """)

        btn.clicked.connect(callback)

        self.menu_layout.addWidget(btn)

    # ==================================================
    # CONTENT AREA
    # ==================================================

    def _build_content_area(self):

        self.content_frame = QtWidgets.QFrame()
        self.content_frame.setStyleSheet("background-color: #ECF0F1;")

        self.layout.addWidget(self.content_frame)

        content_layout = QtWidgets.QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(10, 20, 10, 10)

        self.header_label = QtWidgets.QLabel("")
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet(
            "font-size:18px;font-weight:bold;"
        )

        content_layout.addWidget(self.header_label)

        self.stack = QtWidgets.QStackedWidget()
        content_layout.addWidget(self.stack)

    # ==================================================
    # CREATE PAGES
    # ==================================================

    def _create_pages(self):

        try:

            # STATUS
            self.status_view = StatusView(self.content_frame, self.scan_controller)
            self.stack.addWidget(self.status_view)

            # SCAN
            self.scan_view = ScanView(self.content_frame, self.scan_controller)
            self.stack.addWidget(self.scan_view)

            # PROTECTION
            self.protection_page = self._create_protection_page()
            self.stack.addWidget(self.protection_page)

            # OPTIMIZATION
            self.optimization_page = self._create_optimization_page()
            self.stack.addWidget(self.optimization_page)

            # OUTRAS TELAS

            self.cleaner_view = CleanerView(
                self.content_frame,
                controller=self.cleaner_controller
            )
            self.stack.addWidget(self.cleaner_view)

            self.disk_view = DiskUsageView()
            self.stack.addWidget(self.disk_view)

            self.uninstall_view = UninstallerView(self.content_frame)
            self.stack.addWidget(self.uninstall_view)

            self.settings_view = SecuritySettingsView()
            self.stack.addWidget(self.settings_view)

            self.historic_view = HistoricView(self.scan_controller)
            self.stack.addWidget(self.historic_view)

            self.firewall_view = FirewallView()
            self.stack.addWidget(self.firewall_view)

            self.quarantine_view = QuarantineView(self.quarantine_controller)
            self.stack.addWidget(self.quarantine_view)

            self.custom_scan_view = CustomScanView(self.scan_controller, self)
            self.stack.addWidget(self.custom_scan_view)

        except Exception as e:

            QtWidgets.QMessageBox.critical(
                self,
                "Erro ao inicializar interface",
                str(e)
            )

    # ==================================================
    # PAGE BUILDERS
    # ==================================================

    def _create_protection_page(self):

        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)

        title = QtWidgets.QLabel("Proteção")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:24px;font-weight:bold;")

        layout.addWidget(title)

        self._create_action_button(layout, "Ativação de Firewall", self.show_firewall)
        self._create_action_button(layout, "Verificação de Vírus (Personalizada)", self.show_custom_scan)
        self._create_action_button(layout, "Histórico de Escaneamento", self.show_scan_history)
        self._create_action_button(layout, "Quarentena", self.show_quarantine)

        return page

    # --------------------------------------------------

    def _create_optimization_page(self):

        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)

        self._create_action_button(layout, "Limpeza de Arquivos Temporários", self.show_cleaner)
        self._create_action_button(layout, "Análise de Disco", self.show_disk_usage)
        self._create_action_button(layout, "Desinstalação de Aplicativos", self.show_uninstaller)

        return page

    # --------------------------------------------------

    def _create_action_button(self, layout, text, callback):

        btn = QtWidgets.QPushButton(text)

        btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
            }

            QPushButton:hover {
                background-color: #219150;
            }
        """)

        btn.clicked.connect(callback)

        layout.addWidget(btn)

    # ==================================================
    # STATUS
    # ==================================================

    def show_status(self):
        self.header_label.setText("Status")
        self.stack.setCurrentWidget(self.status_view)

    def run_smart_scan(self):
        self.header_label.setText("Verificação")
        self.stack.setCurrentWidget(self.scan_view)
        self.scan_controller.start_smart_scan()

    def show_scan_view(self):
        self.header_label.setText("Verificação")
        self.stack.setCurrentWidget(self.scan_view)

    # ==================================================
    # PROTECTION
    # ==================================================

    def show_protection(self):
        self.header_label.setText("Proteção")
        self.stack.setCurrentWidget(self.protection_page)

    def show_firewall(self):
        self.header_label.setText("Firewall")
        self.stack.setCurrentWidget(self.firewall_view)

    def show_custom_scan(self):
        self.header_label.setText("Verificação Personalizada")
        self.stack.setCurrentWidget(self.custom_scan_view)

    def show_scan_history(self):
        self.header_label.setText("Histórico de Escaneamento")
        self.stack.setCurrentWidget(self.historic_view)

    def show_quarantine(self):
        self.header_label.setText("Quarentena")
        self.stack.setCurrentWidget(self.quarantine_view)

    # ==================================================
    # OTIMIZAÇÃO
    # ==================================================

    def show_optimization(self):
        self.header_label.setText("Otimização")
        self.stack.setCurrentWidget(self.optimization_page)

    def show_cleaner(self):
        self.header_label.setText("Limpeza")
        self.stack.setCurrentWidget(self.cleaner_view)

    def show_disk_usage(self):
        self.header_label.setText("Uso de Disco")
        self.stack.setCurrentWidget(self.disk_view)

    def show_uninstaller(self):
        self.header_label.setText("Desinstalar Aplicativos")
        self.stack.setCurrentWidget(self.uninstall_view)

    # ==================================================
    # CONFIGURAÇÕES
    # ==================================================

    def show_settings(self):
        self.header_label.setText("Configurações")
        self.stack.setCurrentWidget(self.settings_view)
