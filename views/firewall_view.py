from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QListWidget
)

from PyQt5.QtCore import Qt, QTimer
from datetime import datetime

from controllers.firewall_controller import FirewallController
from views.permissions_view import PermissionsView
from views.wifi_view import WiFiView

from utils.icon_loader import get_icon


class FirewallView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = FirewallController()

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_connections)

        self._build_ui()
        self._update_status()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # -------------------------------------------------
        # ABA 1 — Aplicativos
        # -------------------------------------------------

        permissions_tab = PermissionsView(self.controller)
        tabs.addTab(
            permissions_tab,
            get_icon("apps"),
            "Aplicativos"
        )

        # -------------------------------------------------
        # ABA 2 — Wi-Fi
        # -------------------------------------------------

        wifi_tab = WiFiView(self.controller)
        tabs.addTab(
            wifi_tab,
            get_icon("wifi"),
            "Redes Wi-Fi"
        )

        # -------------------------------------------------
        # ABA 3 — REGRAS FIREWALL
        # -------------------------------------------------

        firewall_rules_tab = QWidget()
        firewall_layout = QVBoxLayout()

        self.title_label = QLabel("Gerenciamento de Regras de Firewall")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.title_label.setStyleSheet(
            "font-size:18px;font-weight:bold;"
        )

        firewall_layout.addWidget(self.title_label)

        # ---------------- LOG ----------------

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(180)

        firewall_layout.addWidget(self.log_area)

        # ---------------- BOTÕES ----------------

        add_rule_button = QPushButton("Adicionar Regra")
        add_rule_button.setIcon(get_icon("shield"))
        add_rule_button.clicked.connect(self.add_rule)

        add_rule_button.setStyleSheet(self._button_blue())

        firewall_layout.addWidget(add_rule_button)

        list_rules_button = QPushButton("Listar Regras Ativas")
        list_rules_button.setIcon(get_icon("list"))
        list_rules_button.clicked.connect(self.list_rules)

        list_rules_button.setStyleSheet(self._button_green())

        firewall_layout.addWidget(list_rules_button)

        # ---------------- STATUS ----------------

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.status_label.setStyleSheet(
            "font-size:14px;font-weight:bold;"
        )

        firewall_layout.addWidget(self.status_label)

        # ---------------- ATIVAR ----------------

        activate_button = QPushButton("Ativar Firewall")
        activate_button.setIcon(get_icon("shield"))
        activate_button.clicked.connect(self.activate_firewall)
        activate_button.setStyleSheet(self._button_green())

        firewall_layout.addWidget(activate_button)

        # ---------------- DESATIVAR ----------------

        deactivate_button = QPushButton("Desativar Firewall")
        deactivate_button.setIcon(get_icon("shield_off"))
        deactivate_button.clicked.connect(self.deactivate_firewall)
        deactivate_button.setStyleSheet(self._button_red())

        firewall_layout.addWidget(deactivate_button)

        firewall_rules_tab.setLayout(firewall_layout)

        tabs.addTab(
            firewall_rules_tab,
            get_icon("firewall"),
            "Regras de Firewall"
        )

        # -------------------------------------------------
        # ABA 4 — MONITOR DE REDE
        # -------------------------------------------------

        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout()

        self.connections_list = QListWidget()

        monitor_layout.addWidget(self.connections_list)

        start_monitor_button = QPushButton("Iniciar Monitoramento")
        start_monitor_button.setIcon(get_icon("play"))
        start_monitor_button.clicked.connect(self.start_monitor)

        start_monitor_button.setStyleSheet(self._button_blue())

        monitor_layout.addWidget(start_monitor_button)

        stop_monitor_button = QPushButton("Parar Monitoramento")
        stop_monitor_button.setIcon(get_icon("stop"))
        stop_monitor_button.clicked.connect(self.stop_monitor)

        stop_monitor_button.setStyleSheet(self._button_red())

        monitor_layout.addWidget(stop_monitor_button)

        monitor_tab.setLayout(monitor_layout)

        tabs.addTab(
            monitor_tab,
            get_icon("network"),
            "Monitor de Rede"
        )

        layout.addWidget(tabs)

    # =====================================================
    # BOTÕES PADRÃO
    # =====================================================

    def _button_blue(self):

        return """
            QPushButton {
                background-color: #3498DB;
                color: white;
                font-size: 15px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5DADE2;
            }
        """

    def _button_green(self):

        return """
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-size: 15px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ECC71;
            }
        """

    def _button_red(self):

        return """
            QPushButton {
                background-color: #E74C3C;
                color: white;
                font-size: 15px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #EC7063;
            }
        """

    # =====================================================
    # STATUS
    # =====================================================

    def _update_status(self):

        try:
            status = self.controller.get_firewall_status()
        except Exception:
            status = "Desconhecido"

        self.status_label.setText(f"Status do Firewall: {status}")

    # =====================================================
    # AÇÕES
    # =====================================================

    def add_rule(self):

        try:

            self.controller.add_rule(
                "Bloquear Porta 8080",
                8080,
                "TCP",
                "block"
            )

            self.log_message("Regra adicionada: Bloquear Porta 8080")

        except Exception as e:
            self.log_message(f"Erro ao adicionar regra: {e}")

    def list_rules(self):

        try:

            rules = self.controller.list_rules()

            if rules:
                self.log_message("\n".join(rules))
            else:
                self.log_message("Nenhuma regra ativa encontrada.")

        except Exception as e:
            self.log_message(f"Erro ao listar regras: {e}")

    def activate_firewall(self):

        try:

            message = self.controller.activate_firewall()

            QApplication.processEvents()

            self._update_status()

            self.log_message(message)

        except Exception as e:
            self.log_message(f"Erro ao ativar firewall: {e}")

    def deactivate_firewall(self):

        try:

            message = self.controller.deactivate_firewall()

            self._update_status()

            self.log_message(message)

        except Exception as e:
            self.log_message(f"Erro ao desativar firewall: {e}")

    # =====================================================
    # MONITOR DE REDE
    # =====================================================

    def start_monitor(self):

        try:

            self.controller.start_monitoring()

            self.timer.start(3000)

            self.log_message("Monitoramento iniciado")

        except Exception as e:

            self.log_message(f"Erro ao iniciar monitoramento: {e}")

    def stop_monitor(self):

        try:

            self.controller.stop_monitoring()

            self.timer.stop()

            self.log_message("Monitoramento parado")

        except Exception as e:

            self.log_message(f"Erro ao parar monitoramento: {e}")

    def _update_connections(self):

        try:

            connections = self.controller.get_connections()

            self.connections_list.clear()

            for c in connections:
                self.connections_list.addItem(str(c))

        except Exception:
            pass

    # =====================================================
    # LOG
    # =====================================================

    def log_message(self, message: str):

        if not message:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        text = f"[{timestamp}] {message}"

        self.log_area.append(text)

        scrollbar = self.log_area.verticalScrollBar()

        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

        print(text)
