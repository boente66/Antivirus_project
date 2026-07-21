from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.firewall_controller import FirewallController
from models.firewall_contracts import FirewallOperation, OperationStatus
from utils.icon_loader import get_icon
from views.components import MetricCard
from views.admin_dialog import AdminPermissionDialog
from views.firewall_rule_dialog import FirewallRuleDialog
from views.permissions_view import PermissionsView
from views.wifi_view import WiFiView


class FirewallView(QWidget):
    """Interface do Firewall conectada somente a estados confirmados."""

    MUTATIONS = {
        FirewallOperation.ENABLE.value,
        FirewallOperation.DISABLE.value,
        FirewallOperation.ADD_RULE.value,
        FirewallOperation.DELETE_RULE.value,
    }

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller or FirewallController()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_connections)
        self._running_mutations = set()
        self._initial_reads_requested = False
        self._operation_names = {}

        self._build_ui()
        self._connect_controller()
        self._apply_capability(self.controller.capability)
        QTimer.singleShot(0, self.controller.refresh_capability)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)

        metrics = QHBoxLayout()
        self.firewall_metric = MetricCard(
            "Estado do firewall", "Verificando", "Proteção de rede", "firewall", "green"
        )
        self.monitor_metric = MetricCard(
            "Monitoramento", "Parado", "Conexões em tempo real", "network", "blue"
        )
        metrics.addWidget(self.firewall_metric)
        metrics.addWidget(self.monitor_metric)
        layout.addLayout(metrics)

        self.tabs = QTabWidget()
        self.permissions_tab = PermissionsView(self.controller)
        self.wifi_tab = WiFiView(self.controller)
        self.tabs.addTab(self.permissions_tab, get_icon("apps"), "Aplicativos")
        self.tabs.addTab(self.wifi_tab, get_icon("wifi"), "Redes Wi-Fi")
        self.tabs.addTab(self._build_rules_tab(), get_icon("firewall"), "Regras de Firewall")
        self.tabs.addTab(self._build_monitor_tab(), get_icon("network"), "Monitor de Rede")
        layout.addWidget(self.tabs)

    def _build_rules_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("Gerenciamento de Regras de Firewall")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.status_label = QLabel("Verificando capacidade do sistema…")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.rules_list = QListWidget()
        self.rules_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.rules_list.itemSelectionChanged.connect(self._update_write_controls)
        layout.addWidget(self.rules_list)

        rule_actions = QHBoxLayout()
        self.add_rule_button = self._button(
            "Adicionar Regra", "shield", "secondary", self.add_rule
        )
        self.remove_rule_button = self._button(
            "Remover Selecionada", "delete", "danger", self.remove_rule
        )
        self.list_rules_button = self._button(
            "Atualizar Regras", "update", "secondary", self.list_rules
        )
        self.diagnose_button = self._button(
            "Diagnosticar Serviços", "status", "secondary", self.diagnose_firewall
        )
        rule_actions.addWidget(self.add_rule_button)
        rule_actions.addWidget(self.remove_rule_button)
        rule_actions.addWidget(self.list_rules_button)
        rule_actions.addWidget(self.diagnose_button)
        layout.addLayout(rule_actions)

        state_actions = QHBoxLayout()
        self.activate_button = self._button(
            "Ativar Firewall", "shield", "primary", self.activate_firewall
        )
        self.deactivate_button = self._button(
            "Desativar Firewall", "shield_off", "danger", self.deactivate_firewall
        )
        state_actions.addWidget(self.activate_button)
        state_actions.addWidget(self.deactivate_button)
        layout.addLayout(state_actions)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(140)
        layout.addWidget(self.log_area)
        return tab

    def _build_monitor_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.connections_list = QListWidget()
        layout.addWidget(self.connections_list)
        self.start_monitor_button = self._button(
            "Iniciar Monitoramento", "play", "primary", self.start_monitor
        )
        self.stop_monitor_button = self._button(
            "Parar Monitoramento", "stop", "danger", self.stop_monitor
        )
        layout.addWidget(self.start_monitor_button)
        layout.addWidget(self.stop_monitor_button)
        return tab

    @staticmethod
    def _button(text, icon, role, callback):
        button = QPushButton(text)
        button.setIcon(get_icon(icon))
        button.setProperty("role", role)
        button.clicked.connect(callback)
        return button

    def _connect_controller(self):
        self.controller.capability_changed.connect(self._on_capability_changed)
        self.controller.rules_updated.connect(self._display_rules)
        self.controller.operation_started.connect(self._on_operation_started)
        self.controller.awaiting_authorization.connect(self._on_authorization)
        self.controller.operation_completed.connect(self._on_operation_completed)
        self.controller.operation_failed.connect(self._on_operation_failed)
        diagnostics_signal = getattr(self.controller, "diagnostics_updated", None)
        if diagnostics_signal is not None:
            diagnostics_signal.connect(self._show_diagnostics)
        self.controller.log_updated.connect(self.log_message)

    def _on_capability_changed(self, capability):
        self._apply_capability(capability)
        if not self._initial_reads_requested:
            self._initial_reads_requested = True
            if capability.readable:
                self.controller.refresh_status()

    def _apply_capability(self, capability):
        if capability.active is True:
            state = "Ativado"
        elif capability.active is False:
            state = "Desativado"
        else:
            state = "Indisponível"
        self.firewall_metric.set_value(state)
        self.firewall_metric.set_detail(capability.reason or "Estado confirmado pelo sistema")
        self.status_label.setText(
            f"Status do Firewall: {state}\n{capability.reason or ''}".strip()
        )
        self._update_write_controls()

    def _update_write_controls(self):
        capability = self.controller.capability
        writable = capability.writable and not capability.write_blocked
        mutation_running = bool(self._running_mutations)
        enabled = writable and not mutation_running
        self.add_rule_button.setEnabled(enabled)
        selected = self.rules_list.currentItem()
        rule = selected.data(Qt.UserRole) if selected else None
        self.remove_rule_button.setEnabled(
            enabled and rule is not None and rule.editable and not rule.protected
        )
        self.activate_button.setEnabled(enabled and capability.active is not True)
        self.deactivate_button.setEnabled(enabled and capability.active is not False)
        self.list_rules_button.setEnabled(capability.readable and not mutation_running)
        self.diagnose_button.setEnabled(not mutation_running)

    def add_rule(self):
        dialog = FirewallRuleDialog(self)
        if dialog.exec_() == dialog.Accepted:
            if AdminPermissionDialog.request(
                self, "Adicionar uma regra ao Firewall do sistema."
            ):
                self.controller.add_rule(payload=dialog.payload())

    def remove_rule(self):
        item = self.rules_list.currentItem()
        rule = item.data(Qt.UserRole) if item else None
        if rule is None:
            return
        answer = QMessageBox.question(
            self,
            "Remover regra",
            f"Remover a regra '{rule.name}' do UFW?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes and AdminPermissionDialog.request(
            self, f"Remover a regra '{rule.name}' do Firewall do sistema."
        ):
            self.controller.remove_rule(rule.id, rule.version)

    def list_rules(self):
        self.controller.refresh_rules()

    def activate_firewall(self):
        answer = QMessageBox.question(
            self,
            "Ativar Firewall",
            "Ativar o Firewall UFW agora? As regras existentes passarão a ser aplicadas.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes and AdminPermissionDialog.request(
            self, "Ativar o Firewall UFW do sistema."
        ):
            self.controller.activate_firewall()

    def deactivate_firewall(self):
        answer = QMessageBox.warning(
            self,
            "Desativar Firewall",
            "Desativar o Firewall reduz a proteção de rede do sistema. Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes and AdminPermissionDialog.request(
            self, "Desativar o Firewall UFW do sistema."
        ):
            self.controller.deactivate_firewall()

    def diagnose_firewall(self):
        diagnose = getattr(self.controller, "diagnose_firewall", None)
        if diagnose is not None:
            diagnose()

    def _on_operation_started(self, _operation_id, operation):
        self._operation_names[_operation_id] = operation
        if operation in self.MUTATIONS:
            self._running_mutations.add(_operation_id)
            self.status_label.setText("Operação do Firewall em andamento…")
            self._update_write_controls()

    def _on_authorization(self, _operation_id, _reason):
        self.status_label.setText("Aguardando autorização do sistema…")

    def _on_operation_completed(self, result):
        operation = self._operation_names.pop(result.operation_id, None)
        self._operation_finished(result)
        if result.operation_id and result.changed:
            QMessageBox.information(self, "Firewall", result.message)
        if result.changed:
            self.controller.refresh_status()
        elif operation == FirewallOperation.GET_STATUS.value:
            self.controller.refresh_rules()
        elif operation == FirewallOperation.LIST_RULES.value:
            refresh = getattr(self.controller, "refresh_applications", None)
            if refresh is not None:
                refresh()
        if result.changed and operation in {
            FirewallOperation.ADD_RULE.value,
            FirewallOperation.DELETE_RULE.value,
        }:
            refresh = getattr(self.controller, "refresh_applications", None)
            if refresh is not None:
                refresh()

    def _on_operation_failed(self, result):
        operation = self._operation_names.pop(result.operation_id, None)
        self._operation_finished(result)
        if operation == FirewallOperation.DIAGNOSE.value:
            return
        if result.status == OperationStatus.CANCELLED.value:
            QMessageBox.information(self, "Autorização cancelada", result.message)
        elif result.status not in {
            OperationStatus.UNSUPPORTED.value,
            OperationStatus.BACKEND_CONFLICT.value,
        }:
            QMessageBox.warning(self, "Operação não concluída", result.message)

    def _operation_finished(self, result):
        self._running_mutations.discard(result.operation_id)
        self._apply_capability(self.controller.capability)

    def _display_rules(self, rules):
        self.rules_list.clear()
        for rule in rules:
            if rule.application:
                port = f"perfil: {rule.application}"
            else:
                port = str(rule.port_start)
            if not rule.application and rule.port_end != rule.port_start:
                port = f"{rule.port_start}-{rule.port_end}"
            text = (
                f"{rule.name} | {rule.action.upper()} {rule.direction.upper()} | "
                f"{port}{'' if rule.application else '/' + rule.protocol} | "
                f"origem: {rule.source}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, rule)
            if rule.protected or not rule.editable:
                item.setToolTip("Regra externa/protegida: remoção desabilitada.")
            self.rules_list.addItem(item)
        self._update_write_controls()

    def _show_diagnostics(self, result):
        state = result.confirmed_state if isinstance(result.confirmed_state, dict) else {}
        checks = state.get("checks", {})
        problems = list(state.get("problems", ()))
        lines = [
            f"UFW instalado: {'sim' if checks.get('ufw_installed') else 'não'}",
            f"Polkit/pkexec: {'sim' if checks.get('pkexec_installed') else 'não'}",
        ]
        if checks.get("ufw_service_enabled") is not None:
            lines.append(
                "Serviço habilitado no boot: "
                + ("sim" if checks.get("ufw_service_enabled") else "não")
            )
        if problems:
            lines.extend(["", "Problemas:", *[f"• {item}" for item in problems]])
        QMessageBox.information(self, "Diagnóstico do Firewall", "\n".join(lines))

    def start_monitor(self):
        self.controller.start_monitoring()
        self.timer.start(3000)
        self.monitor_metric.set_value("Ativo")
        self.monitor_metric.set_detail("Atualização a cada 3 segundos")
        self.log_message("Monitoramento iniciado")

    def stop_monitor(self):
        self.controller.stop_monitoring()
        self.timer.stop()
        self.monitor_metric.set_value("Parado")
        self.monitor_metric.set_detail("Monitoramento interrompido")
        self.log_message("Monitoramento parado")

    def _update_connections(self):
        self.connections_list.clear()
        for connection in self.controller.get_connections():
            self.connections_list.addItem(str(connection))

    def log_message(self, message):
        if not message:
            return
        text = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_area.append(text)
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        self.timer.stop()
        self.controller.stop_monitoring()
        if not self.controller.shutdown():
            self.log_message(
                "A operação administrativa ainda está finalizando; aguarde para fechar."
            )
            event.ignore()
            return
        super().closeEvent(event)
