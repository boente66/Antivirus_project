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
from views.browser_process_dialog import BrowserProcessWarningDialog
from views.components import FeatureCard

from utils.icon_loader import get_icon


class MainView(QtWidgets.QMainWindow):

    DEFAULT_SIZE = QtCore.QSize(1180, 760)
    COMPACT_MINIMUM_SIZE = QtCore.QSize(800, 600)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Antivírus")
        self.setMinimumSize(self.COMPACT_MINIMUM_SIZE)
        self.resize(self.DEFAULT_SIZE)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, True)

        # --------------------------------------------------
        # Controllers
        # --------------------------------------------------

        self.quarantine_controller = QuarantineController()
        self.scan_controller = ScanController(
            parent=self,
            quarantine_service=self.quarantine_controller.service
        )
        self.cleaner_controller = CleanerController()
        self.scan_controller.browser_warning_requested.connect(
            self._show_browser_process_warning
        )

        # --------------------------------------------------
        # Layout principal
        # --------------------------------------------------

        self.central_widget = QtWidgets.QWidget()
        self.central_widget.setObjectName("AppRoot")
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
        self.menu_frame.setObjectName("Sidebar")
        self.menu_frame.setFixedWidth(210)

        self.layout.addWidget(self.menu_frame)

        self.menu_layout = QtWidgets.QVBoxLayout(self.menu_frame)
        self.menu_layout.setContentsMargins(14, 20, 14, 18)
        self.menu_layout.setSpacing(7)
        self.menu_layout.setAlignment(QtCore.Qt.AlignTop)

        brand_layout = QtWidgets.QHBoxLayout()
        brand_icon = QtWidgets.QLabel()
        brand_icon.setPixmap(get_icon("shield").pixmap(34, 34))
        brand_layout.addWidget(brand_icon)
        brand_text = QtWidgets.QVBoxLayout()
        brand_text.setSpacing(0)
        brand_title = QtWidgets.QLabel("Antivírus")
        brand_title.setObjectName("BrandTitle")
        self.brand_subtitle = QtWidgets.QLabel("Proteção do sistema")
        self.brand_subtitle.setObjectName("BrandSubtitle")
        brand_text.addWidget(brand_title)
        brand_text.addWidget(self.brand_subtitle)
        brand_layout.addLayout(brand_text, 1)
        self.menu_layout.addLayout(brand_layout)
        self.menu_layout.addSpacing(24)

        self.nav_buttons = {}

        self._create_menu_button("status", "Status", "status", self.show_status)
        self._create_menu_button("protection", "Proteção", "shield", self.show_protection)
        self._create_menu_button("optimization", "Otimização", "cleaner", self.show_optimization)
        self._create_menu_button("settings", "Configurações", "settings", self.show_settings)

        self.menu_layout.addStretch()

        self.sidebar_status_panel = QtWidgets.QFrame()
        self.sidebar_status_panel.setObjectName("SidebarStatus")
        status_layout = QtWidgets.QVBoxLayout(self.sidebar_status_panel)
        status_layout.setContentsMargins(13, 13, 13, 13)
        status_title = QtWidgets.QLabel("●  Proteção monitorada")
        status_title.setObjectName("SidebarStatusTitle")
        status_text = QtWidgets.QLabel(
            "ClamAV e módulos de segurança disponíveis no painel."
        )
        status_text.setObjectName("SidebarStatusText")
        status_text.setWordWrap(True)
        status_layout.addWidget(status_title)
        status_layout.addWidget(status_text)
        self.menu_layout.addWidget(self.sidebar_status_panel)
        self.menu_layout.addSpacing(10)

        version_label = QtWidgets.QLabel("✓  Versão 1.0.0")
        version_label.setObjectName("SidebarCaption")
        self.menu_layout.addWidget(version_label)

    # --------------------------------------------------

    def _create_menu_button(self, key, text, icon, callback):

        btn = QtWidgets.QPushButton(text)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setProperty("nav", True)
        btn.setIcon(get_icon(icon))
        btn.setIconSize(QtCore.QSize(21, 21))
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        self.menu_layout.addWidget(btn)
        self.nav_buttons[key] = btn

    # ==================================================
    # CONTENT AREA
    # ==================================================

    def _build_content_area(self):

        self.content_frame = QtWidgets.QFrame()
        self.content_frame.setObjectName("ContentFrame")

        self.layout.addWidget(self.content_frame)

        self.content_layout = QtWidgets.QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(22, 14, 22, 18)
        self.content_layout.setSpacing(10)

        self.header_label = QtWidgets.QLabel("")
        self.header_label.setObjectName("PageTitle")

        self.content_layout.addWidget(self.header_label)

        self.stack = QtWidgets.QStackedWidget()
        self.content_layout.addWidget(self.stack)

    # ==================================================
    # CREATE PAGES
    # ==================================================

    def _create_pages(self):

        try:

            # STATUS
            self.status_view = StatusView(
                self.content_frame,
                self.scan_controller,
                navigation={
                    "firewall": self.show_firewall,
                    "quarantine": self.show_quarantine,
                    "history": self.show_scan_history,
                    "custom_scan": self.show_custom_scan,
                },
            )
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

            self.settings_view = SecuritySettingsView(self.scan_controller)
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
        layout = QtWidgets.QGridLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(14)

        cards = [
            FeatureCard(
                "Firewall",
                "Controle conexões e regras de proteção da rede.",
                "Abrir Firewall",
                "firewall",
                "Módulo disponível",
            ),
            FeatureCard(
                "Verificação personalizada",
                "Escolha pastas e locais específicos para analisar.",
                "Selecionar e verificar",
                "scan",
                "Análise sob demanda",
            ),
            FeatureCard(
                "Histórico de escaneamento",
                "Consulte verificações, ameaças e ações registradas.",
                "Ver histórico",
                "history",
                "Registros auditáveis",
            ),
            FeatureCard(
                "Quarentena",
                "Revise arquivos isolados e escolha ações seguras.",
                "Abrir quarentena",
                "quarantine",
                "Armazenamento protegido",
            ),
        ]
        callbacks = [
            self.show_firewall,
            self.show_custom_scan,
            self.show_scan_history,
            self.show_quarantine,
        ]
        for index, (card, callback) in enumerate(zip(cards, callbacks)):
            card.activated.connect(callback)
            layout.addWidget(card, index // 2, index % 2)
        layout.setRowStretch(2, 1)
        self.protection_cards = cards
        self.protection_layout = layout

        return page

    # --------------------------------------------------

    def _create_optimization_page(self):

        page = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(14)

        cards = [
            FeatureCard(
                "Limpeza do sistema",
                "Analise caches, temporários e outros itens desnecessários.",
                "Iniciar limpeza",
                "cleaner",
                "Análise segura antes da remoção",
            ),
            FeatureCard(
                "Uso de disco",
                "Descubra quais diretórios ocupam mais espaço.",
                "Analisar disco",
                "disk",
                "Visualização por volume",
            ),
            FeatureCard(
                "Aplicativos instalados",
                "Consulte e remova programas com acompanhamento técnico.",
                "Gerenciar aplicativos",
                "apps",
                "Desinstalação acompanhada",
            ),
        ]
        callbacks = [self.show_cleaner, self.show_disk_usage, self.show_uninstaller]
        for index, (card, callback) in enumerate(zip(cards, callbacks)):
            card.activated.connect(callback)
            layout.addWidget(card, 0, index)
        layout.setRowStretch(1, 1)
        self.optimization_cards = cards
        self.optimization_layout = layout

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
        self._set_active_nav("status")

    def run_smart_scan(self):
        self.header_label.setText("Verificação")
        self.stack.setCurrentWidget(self.scan_view)
        self._set_active_nav("protection")
        self.scan_controller.start_smart_scan()

    def show_scan_view(self):
        self.header_label.setText("Verificação")
        self.stack.setCurrentWidget(self.scan_view)
        self._set_active_nav("protection")

    # ==================================================
    # PROTECTION
    # ==================================================

    def show_protection(self):
        self.header_label.setText("Proteção")
        self.stack.setCurrentWidget(self.protection_page)
        self._set_active_nav("protection")

    def show_firewall(self):
        self.header_label.setText("Firewall")
        self.stack.setCurrentWidget(self.firewall_view)
        self._set_active_nav("protection")

    def show_custom_scan(self):
        self.header_label.setText("Verificação Personalizada")
        self.stack.setCurrentWidget(self.custom_scan_view)
        self._set_active_nav("protection")

    def show_scan_history(self):
        self.header_label.setText("Histórico de Escaneamento")
        self.stack.setCurrentWidget(self.historic_view)
        self._set_active_nav("protection")

    def show_quarantine(self):
        self.header_label.setText("Quarentena")
        self.stack.setCurrentWidget(self.quarantine_view)
        self._set_active_nav("protection")

    # ==================================================
    # OTIMIZAÇÃO
    # ==================================================

    def show_optimization(self):
        self.header_label.setText("Otimização")
        self.stack.setCurrentWidget(self.optimization_page)
        self._set_active_nav("optimization")

    def show_cleaner(self):
        self.header_label.setText("Limpeza")
        self.stack.setCurrentWidget(self.cleaner_view)
        self._set_active_nav("optimization")

    def show_disk_usage(self):
        self.header_label.setText("Uso de Disco")
        self.stack.setCurrentWidget(self.disk_view)
        self._set_active_nav("optimization")

    def show_uninstaller(self):
        self.header_label.setText("Desinstalar Aplicativos")
        self.stack.setCurrentWidget(self.uninstall_view)
        self._set_active_nav("optimization")

    # ==================================================
    # CONFIGURAÇÕES
    # ==================================================

    def show_settings(self):
        self.header_label.setText("Configurações")
        self.stack.setCurrentWidget(self.settings_view)
        self._set_active_nav("settings")

    def _set_active_nav(self, key):
        button = self.nav_buttons.get(key)
        if button is not None:
            button.setChecked(True)

    def resizeEvent(self, event):
        compact = self.width() < 980
        self.menu_frame.setFixedWidth(178 if compact else 210)
        self.brand_subtitle.setVisible(not compact)
        self.sidebar_status_panel.setVisible(self.height() >= 680)
        margin = 14 if compact else 22
        self.content_layout.setContentsMargins(margin, 12, margin, 14)

        if hasattr(self, "optimization_cards"):
            columns = 1 if self.width() < 980 else 3
            for index, card in enumerate(self.optimization_cards):
                self.optimization_layout.addWidget(
                    card, index // columns, index % columns
                )
        super().resizeEvent(event)

    def _show_browser_process_warning(self, browsers):
        dialog = BrowserProcessWarningDialog(browsers, self)
        accepted = dialog.exec_() == QtWidgets.QDialog.Accepted
        self.scan_controller.resolve_browser_warning(
            continue_scan=accepted,
            dont_show_again=dialog.dont_show_again(),
        )
