from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal

from models.firewall_contracts import (
    FirewallOperation,
    FirewallOperationRequest,
    FirewallOperationResult,
    OperationStatus,
)
from services.firewall_service import FirewallService
from workers.firewall_worker import FirewallWorker


class FirewallController(QObject):
    capability_changed = pyqtSignal(object)
    rules_updated = pyqtSignal(list)
    applications_updated = pyqtSignal(list)
    diagnostics_updated = pyqtSignal(object)
    status_changed = pyqtSignal(object)
    operation_started = pyqtSignal(str, str)
    awaiting_authorization = pyqtSignal(str, str)
    operation_progress = pyqtSignal(str, int)
    operation_completed = pyqtSignal(object)
    operation_failed = pyqtSignal(object)
    log_updated = pyqtSignal(str)

    MAX_LOGS = 500

    def __init__(self, service=None, worker_factory=None, parent=None):
        super().__init__(parent)
        self.firewall_service = service or FirewallService()
        self.worker_factory = worker_factory or FirewallWorker
        self._workers = {}
        self._active_mutation = None
        self._active_rules = set()
        self.permissions = []
        self.wifi_networks = []
        self.logs = []

    @property
    def capability(self):
        return self.firewall_service.capability

    def refresh_capability(self):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.DETECT_CAPABILITY,
            reason="Atualizar capacidade do Firewall.",
        ))

    def refresh_status(self):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.GET_STATUS,
            reason="Atualizar estado real do Firewall.",
        ))

    def refresh_rules(self):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.LIST_RULES,
            reason="Atualizar regras confirmadas pelo backend.",
        ))

    def refresh_applications(self):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.LIST_APPLICATIONS,
            reason="Listar perfis de aplicação registrados no UFW.",
        ))

    def diagnose_firewall(self):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.DIAGNOSE,
            reason="Diagnosticar componentes e serviço do Firewall.",
        ))

    def activate_firewall(self):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.ENABLE,
            reason="Ativar o Firewall UFW.",
        ))

    def deactivate_firewall(self):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.DISABLE,
            reason="Desativar o Firewall UFW.",
        ))

    def add_rule(self, name=None, port=None, protocol="tcp", action="deny", payload=None):
        data = dict(payload or {})
        if not data:
            data = {
                "name": name,
                "port": port,
                "protocol": protocol,
                "action": "deny" if action == "block" else action,
                "direction": "in",
                "source": "any",
                "destination": "any",
            }
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.ADD_RULE,
            payload=data,
            reason=f"Criar regra {data.get('name') or ''}".strip(),
        ))

    def remove_rule(self, rule_id, expected_version=None):
        return self._start(FirewallOperationRequest.create(
            FirewallOperation.DELETE_RULE,
            rule_id=rule_id,
            expected_version=expected_version,
            reason="Remover uma regra UFW identificada.",
        ))

    def list_rules(self):
        return list(self.firewall_service.snapshot_rules())

    def get_firewall_status(self):
        active = self.capability.active
        if active is True:
            return "Ativado"
        if active is False:
            return "Desativado"
        return self.capability.reason or "Status desconhecido"

    def _start(self, request):
        is_mutation = request.operation in self.firewall_service.MUTATIONS
        if is_mutation and self._active_mutation is not None:
            self._emit_busy(request)
            return None
        if request.rule_id and request.rule_id in self._active_rules:
            self._emit_busy(request)
            return None

        worker = self.worker_factory(self.firewall_service, request, self)
        operation_id = request.operation_id
        self._workers[operation_id] = worker
        if is_mutation:
            self._active_mutation = operation_id
        if request.rule_id:
            self._active_rules.add(request.rule_id)

        worker.operation_started.connect(self._forward_started)
        worker.awaiting_authorization.connect(self.awaiting_authorization.emit)
        worker.progress.connect(self.operation_progress.emit)
        worker.completed.connect(
            lambda result, current=worker: self._handle_result(result, current, True)
        )
        worker.failed.connect(
            lambda result, current=worker: self._handle_result(result, current, False)
        )
        worker.finished.connect(
            lambda op_id=operation_id, rule_id=request.rule_id, mutation=is_mutation:
            self._cleanup_worker(op_id, rule_id, mutation)
        )
        worker.start()
        return operation_id

    def _forward_started(self, operation_id, operation):
        if operation_id not in self._workers:
            return
        self.operation_started.emit(operation_id, operation)
        self.log_action(f"Operação iniciada: {operation}")

    def _handle_result(self, result, worker, success):
        current = self._workers.get(result.operation_id)
        if current is not worker:
            return
        # A operação de sistema terminou antes de o sinal chegar à View;
        # libera os guards sem aguardar a destruição posterior da QThread.
        if self._active_mutation == result.operation_id:
            self._active_mutation = None
        request = getattr(worker, "request", None)
        if request and request.rule_id:
            self._active_rules.discard(request.rule_id)
        operation = getattr(getattr(worker, "request", None), "operation", None)
        if operation == FirewallOperation.LIST_APPLICATIONS.value:
            self.applications_updated.emit(list(result.confirmed_state or ()))
        elif isinstance(result.confirmed_state, tuple):
            self.rules_updated.emit(list(result.confirmed_state))
        elif operation in {
            FirewallOperation.ADD_RULE.value,
            FirewallOperation.DELETE_RULE.value,
        }:
            self.rules_updated.emit(list(self.firewall_service.snapshot_rules()))

        if operation == FirewallOperation.DETECT_CAPABILITY.value:
            self.capability_changed.emit(self.capability)
        elif operation == FirewallOperation.DIAGNOSE.value:
            self.diagnostics_updated.emit(result)
        elif operation in {
            FirewallOperation.GET_STATUS.value,
            FirewallOperation.ENABLE.value,
            FirewallOperation.DISABLE.value,
        }:
            self.capability_changed.emit(self.capability)

        if isinstance(result.confirmed_state, dict) and "active" in result.confirmed_state:
            self.status_changed.emit(result)
        self.log_action(result.message)
        if success:
            self.operation_completed.emit(result)
        else:
            self.operation_failed.emit(result)

    def _cleanup_worker(self, operation_id, rule_id, mutation):
        worker = self._workers.pop(operation_id, None)
        if worker:
            worker.deleteLater()
        if mutation and self._active_mutation == operation_id:
            self._active_mutation = None
        if rule_id:
            self._active_rules.discard(rule_id)

    def _emit_busy(self, request):
        result = FirewallOperationResult(
            operation_id=request.operation_id,
            status=OperationStatus.BUSY.value,
            backend=self.capability.backend,
            verified=False,
            error_code="mutation_in_progress",
            message="Outra alteração do Firewall está em andamento.",
        )
        self.operation_failed.emit(result)

    def shutdown(self, timeout_ms=3000):
        workers = list(self._workers.values())
        for worker in workers:
            worker.cancel()
        for worker in workers:
            if worker.isRunning():
                worker.wait(max(0, int(timeout_ms)))
        return not any(worker.isRunning() for worker in workers)

    def add_permission(self, app_name, allow_traffic):
        return self.add_rule(payload={
            "name": f"Aplicação {app_name}",
            "application": app_name,
            "action": "allow" if allow_traffic else "deny",
            "direction": "in",
            "comment": "Regra de perfil criada pelo Antivírus",
        })

    def remove_permission(self, profile):
        rule_id = getattr(profile, "rule_id", None)
        version = getattr(profile, "rule_version", None)
        if not rule_id or version is None or not getattr(profile, "managed", False):
            return self._unsupported_local(
                "Somente regras de aplicação criadas pelo Antivírus podem ser removidas."
            )
        return self.remove_rule(rule_id, version)

    def get_permissions(self):
        return list(self.firewall_service.snapshot_applications())

    def notify_impact(self, app_name):
        return (
            f"O bloqueio do perfil '{app_name}' afeta as portas publicadas pelo UFW. "
            "Ele não encerra o programa nem implementa bloqueio por processo."
        )

    def scan_wifi_networks(self):
        try:
            adapter = getattr(self.firewall_service, "platform_adapter", None)
            networks = adapter.scan_wifi_networks() if adapter else []
            return [dict(network) for network in networks if isinstance(network, dict)]
        except Exception:
            return []

    def add_wifi_network(self, ssid, allow_traffic):
        return self._unsupported_local("Regras por rede Wi-Fi ainda não são suportadas.")

    def remove_wifi_network(self, ssid):
        return self._unsupported_local("Regras por rede Wi-Fi ainda não são suportadas.")

    def get_wifi_networks(self):
        return []

    def start_monitoring(self):
        self.firewall_service.monitor_service.start() if hasattr(self.firewall_service, "monitor_service") else None

    def stop_monitoring(self):
        self.firewall_service.monitor_service.stop() if hasattr(self.firewall_service, "monitor_service") else None

    def get_connections(self):
        monitor = getattr(self.firewall_service, "monitor_service", None)
        return monitor.get_connections() if monitor else []

    def _unsupported_local(self, message):
        result = FirewallOperationResult(
            operation_id=f"local-unsupported-{datetime.now().timestamp()}",
            status=OperationStatus.UNSUPPORTED.value,
            backend=self.capability.backend,
            verified=False,
            error_code="unsupported",
            message=message,
        )
        self.operation_failed.emit(result)
        return result

    def log_action(self, action):
        if not action:
            return
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {action}"
        self.logs.append(entry)
        if len(self.logs) > self.MAX_LOGS:
            self.logs.pop(0)
        self.log_updated.emit(entry)

    def get_logs(self):
        return list(self.logs)
