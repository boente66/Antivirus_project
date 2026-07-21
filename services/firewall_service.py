import threading

from core.platform.platform_factory import PlatformFactory
from database.repositories.firewall_audit_repository import FirewallAuditRepository
from models.firewall_contracts import (
    FirewallApplicationProfile,
    FirewallCapability,
    FirewallOperation,
    FirewallOperationRequest,
    FirewallOperationResult,
    OperationStatus,
    PrivilegeRequirement,
    SupportStatus,
)
from services.firewall_detector import FirewallDetector
from services.firewall_monitor_service import FirewallMonitorService
from services.firewall_validation_service import (
    FirewallValidationError,
    FirewallValidationService,
)


class FirewallService:
    """Coordena capacidade, validação, backend e estado confirmado."""

    MUTATIONS = {
        FirewallOperation.ENABLE.value,
        FirewallOperation.DISABLE.value,
        FirewallOperation.ADD_RULE.value,
        FirewallOperation.DELETE_RULE.value,
    }

    def __init__(
        self,
        detector=None,
        adapter=None,
        audit_repository=None,
        validation_service=None,
        platform_adapter=None,
    ):
        self.detector = detector or FirewallDetector()
        self.adapter = adapter
        self._adapter_injected = adapter is not None
        self.audit_repository = audit_repository or FirewallAuditRepository()
        self.validation = validation_service or FirewallValidationService()
        self.platform_adapter = platform_adapter
        # O monitor continua independente do fluxo de mutação do Firewall.
        # Mantém o contrato legado sem criar uma segunda fonte de regras.
        self.monitor_service = FirewallMonitorService()
        self.capability = FirewallCapability(
            platform="unknown",
            backend="unknown",
            installed=False,
            active=None,
            readable=False,
            writable=False,
            requires_privilege=True,
            support_status=SupportStatus.UNAVAILABLE.value,
            reason="Capacidade ainda não verificada.",
        )
        self._capability_loaded = False
        self._rules = []
        self._rules_loaded = False
        self._applications = []
        self._mutation_lock = threading.Lock()

    @property
    def engine_type(self):
        return self.capability.backend

    def get_privilege_requirement(self, request):
        operation = str(request.operation)
        required = operation in self.MUTATIONS or operation in {
            FirewallOperation.GET_STATUS.value,
            FirewallOperation.LIST_RULES.value,
            FirewallOperation.LIST_APPLICATIONS.value,
        }
        return PrivilegeRequirement(
            required=required,
            operation=operation,
            reason=(
                "Esta operação requer acesso administrativo ao backend do Firewall."
                if required else "Operação somente de leitura sem elevação."
            ),
            scope=self._scope_for(request),
            backend=self.capability.backend,
            can_prompt=required and bool(self.capability.readable or self.capability.writable),
        )

    def execute(self, request):
        if not isinstance(request, FirewallOperationRequest):
            return self._result(
                "unknown",
                OperationStatus.INVALID_REQUEST,
                "request_contract_required",
                "A operação deve usar FirewallOperationRequest.",
            )
        try:
            operation = FirewallOperation(request.operation)
        except ValueError:
            return self._result(
                request.operation_id,
                OperationStatus.INVALID_REQUEST,
                "operation_not_supported",
                "Operação de Firewall inválida.",
            )

        if operation == FirewallOperation.DETECT_CAPABILITY:
            return self._detect_capability(request)

        if not self._capability_loaded:
            detection = self._detect_capability(
                FirewallOperationRequest.create(
                    FirewallOperation.DETECT_CAPABILITY,
                    requested_by=request.requested_by,
                    reason="Pré-requisito da operação.",
                )
            )
            if detection.status not in {
                OperationStatus.SUCCESS.value,
                OperationStatus.UNSUPPORTED.value,
                OperationStatus.BACKEND_CONFLICT.value,
            }:
                return self._replace_operation_id(detection, request.operation_id)

        if operation in self.MUTATIONS and self.capability.write_blocked:
            status = (
                OperationStatus.BACKEND_CONFLICT
                if self.capability.support_status == SupportStatus.BACKEND_CONFLICT.value
                else OperationStatus.UNSUPPORTED
            )
            result = self._result(
                request.operation_id,
                status,
                "write_not_supported",
                self.capability.reason or "Escrita não suportada neste backend.",
            )
            self._safe_audit("execution_failed", request, result=result)
            return result

        if operation == FirewallOperation.GET_STATUS:
            return self._read_status(request)
        if operation == FirewallOperation.LIST_RULES:
            return self._list_rules(request)
        if operation == FirewallOperation.LIST_APPLICATIONS:
            return self._list_applications(request)
        if operation == FirewallOperation.DIAGNOSE:
            return self._diagnose(request)

        if not self._mutation_lock.acquire(blocking=False):
            result = self._result(
                request.operation_id,
                OperationStatus.BUSY,
                "mutation_in_progress",
                "Outra alteração do Firewall está em andamento.",
            )
            self._safe_audit("execution_failed", request, result=result)
            return result
        try:
            return self._execute_mutation(operation, request)
        finally:
            self._mutation_lock.release()

    def snapshot_rules(self):
        return tuple(self._rules)

    def snapshot_applications(self):
        return tuple(self._applications)

    def _detect_capability(self, request):
        try:
            capability = self.detector.detect_capability()
        except Exception as exc:
            capability = FirewallCapability(
                platform="unknown",
                backend="unknown",
                installed=False,
                active=None,
                readable=False,
                writable=False,
                requires_privilege=True,
                support_status=SupportStatus.UNAVAILABLE.value,
                reason=f"Falha ao detectar backend: {exc}",
            )
        self.capability = capability
        self._capability_loaded = True
        if not self._adapter_injected:
            self.adapter = self._adapter_for(capability)

        status = (
            OperationStatus.SUCCESS
            if capability.support_status in {
                SupportStatus.SUPPORTED.value,
                SupportStatus.READ_ONLY.value,
            }
            else OperationStatus.BACKEND_CONFLICT
            if capability.support_status == SupportStatus.BACKEND_CONFLICT.value
            else OperationStatus.UNSUPPORTED
        )
        result = FirewallOperationResult(
            operation_id=request.operation_id,
            status=status.value,
            backend=capability.backend,
            confirmed_state=capability,
            changed=False,
            verified=True,
            error_code=None if status == OperationStatus.SUCCESS else capability.support_status,
            message=capability.reason,
        )
        self._safe_audit("capability_detected", request, result=result)
        return result

    def _adapter_for(self, capability):
        try:
            platform_adapter = (
                self.platform_adapter
                or getattr(self.detector, "platform_adapter", None)
                or PlatformFactory.create()
            )
        except Exception:
            return None
        self.platform_adapter = platform_adapter
        return platform_adapter.create_firewall_adapter(
            getattr(self.detector, "executor", None)
        )

    def _read_status(self, request):
        if not self.adapter or not self.capability.readable:
            result = self._result(
                request.operation_id,
                OperationStatus.UNSUPPORTED,
                "status_unavailable",
                self.capability.reason or "Status indisponível.",
            )
        else:
            result = self.adapter.read_status(request.operation_id)
            if result.succeeded and isinstance(result.confirmed_state, dict):
                active = result.confirmed_state.get("active")
                self.capability = FirewallCapability(
                    **{**self.capability.__dict__, "active": active}
                )
        self._safe_audit("operation_completed", request, result=result)
        return result

    def _list_rules(self, request):
        result, rules = self._refresh_rules(request.operation_id)
        if result.succeeded:
            result = FirewallOperationResult(
                **{**result.__dict__, "confirmed_state": tuple(rules)}
            )
        self._safe_audit("operation_completed", request, result=result)
        return result

    def _list_applications(self, request):
        if not self.adapter or not hasattr(self.adapter, "list_firewall_applications"):
            result = self._result(
                request.operation_id,
                OperationStatus.UNSUPPORTED,
                "application_listing_unsupported",
                "Perfis de aplicação não são suportados neste backend.",
            )
            self._safe_audit("operation_completed", request, result=result)
            return result
        if self._rules_loaded:
            rules = list(self._rules)
        else:
            rules_result, rules = self._refresh_rules(
                f"{request.operation_id}:rules"
            )
            if not rules_result.succeeded:
                self._safe_audit("operation_completed", request, result=rules_result)
                return self._replace_operation_id(rules_result, request.operation_id)
        result, profiles = self.adapter.list_firewall_applications(
            request.operation_id
        )
        if result.succeeded:
            application_rules = {
                rule.application: rule for rule in rules if rule.application
            }
            self._applications = [
                FirewallApplicationProfile(
                    name=profile.name,
                    action=(
                        application_rules[profile.name].action
                        if profile.name in application_rules else None
                    ),
                    rule_id=(
                        application_rules[profile.name].id
                        if profile.name in application_rules else None
                    ),
                    rule_version=(
                        application_rules[profile.name].version
                        if profile.name in application_rules else None
                    ),
                    managed=(
                        profile.name in application_rules
                        and application_rules[profile.name].editable
                        and not application_rules[profile.name].protected
                    ),
                )
                for profile in profiles
            ]
            result = FirewallOperationResult(
                **{**result.__dict__, "confirmed_state": tuple(self._applications)}
            )
        self._safe_audit("operation_completed", request, result=result)
        return result

    def _diagnose(self, request):
        if not self.adapter or not hasattr(self.adapter, "diagnose_firewall"):
            result = self._result(
                request.operation_id,
                OperationStatus.UNSUPPORTED,
                "diagnostic_unsupported",
                "Diagnóstico não suportado neste backend.",
            )
        else:
            result = self.adapter.diagnose_firewall(request.operation_id)
        self._safe_audit("operation_completed", request, result=result)
        return result

    def _execute_mutation(self, operation, request):
        requested_event = {
            FirewallOperation.ADD_RULE: "rule_create_requested",
            FirewallOperation.DELETE_RULE: "rule_remove_requested",
            FirewallOperation.ENABLE: "firewall_enable_requested",
            FirewallOperation.DISABLE: "firewall_disable_requested",
        }[operation]
        if not self._audit(requested_event, request):
            return self._result(
                request.operation_id,
                OperationStatus.AUDIT_FAILED,
                "audit_failed",
                "A intenção não pôde ser auditada; operação não executada.",
            )
        self._safe_audit("privilege_requested", request)

        if operation == FirewallOperation.ENABLE:
            result = self.adapter.enable(request.operation_id)
            return self._finish_mutation(request, result)
        if operation == FirewallOperation.DISABLE:
            result = self.adapter.disable(request.operation_id)
            return self._finish_mutation(request, result)
        if operation == FirewallOperation.ADD_RULE:
            return self._add_rule(request)
        if operation == FirewallOperation.DELETE_RULE:
            return self._delete_rule(request)
        return self._result(
            request.operation_id,
            OperationStatus.INVALID_REQUEST,
            "mutation_unknown",
            "Mutação desconhecida.",
        )

    def _add_rule(self, request):
        try:
            requested_rule = self.validation.normalize_rule(
                request.payload,
                backend=self.capability.backend,
                platform=self.capability.platform,
            )
        except FirewallValidationError as exc:
            result = self._result(
                request.operation_id,
                OperationStatus.INVALID_REQUEST,
                exc.code,
                str(exc),
            )
            self._safe_audit("rule_create_failed", request, result=result)
            return result

        current_result, current_rules = self._refresh_rules(
            f"{request.operation_id}:precheck"
        )
        if not current_result.succeeded:
            return self._finish_mutation(request, current_result, requested_rule)
        if any(self.adapter.rules_match(rule, requested_rule) for rule in current_rules):
            result = self._result(
                request.operation_id,
                OperationStatus.CONFLICT,
                "duplicate_rule",
                "Já existe uma regra equivalente no UFW.",
                requested_state=requested_rule.to_dict(),
            )
            self._safe_audit("rule_create_failed", request, result=result, rule=requested_rule)
            return result

        result = self.adapter.add_rule(request.operation_id, requested_rule)
        return self._finish_mutation(request, result, requested_rule)

    def _delete_rule(self, request):
        current_result, current_rules = self._refresh_rules(
            f"{request.operation_id}:precheck"
        )
        if not current_result.succeeded:
            return self._finish_mutation(request, current_result)
        rule = next((item for item in current_rules if item.id == request.rule_id), None)
        if rule is None:
            result = self._result(
                request.operation_id,
                OperationStatus.CONFLICT,
                "external_change_detected",
                "A regra mudou ou deixou de existir. Atualize a listagem.",
            )
            self._safe_audit("external_change_detected", request, result=result)
            return result
        if request.expected_version is None or request.expected_version != rule.version:
            result = self._result(
                request.operation_id,
                OperationStatus.CONFLICT,
                "version_conflict",
                "A versão da regra não corresponde ao estado atual.",
                requested_state=rule.to_dict(),
            )
            self._safe_audit("external_change_detected", request, result=result, rule=rule)
            return result
        if rule.protected or not rule.editable:
            result = self._result(
                request.operation_id,
                OperationStatus.DENIED,
                "rule_protected",
                "Esta regra é externa ou protegida e não pode ser removida.",
                requested_state=rule.to_dict(),
            )
            self._safe_audit("rule_remove_failed", request, result=result, rule=rule)
            return result

        result = self.adapter.delete_rule(request.operation_id, rule)
        return self._finish_mutation(request, result, rule)

    def _finish_mutation(self, request, result, rule=None):
        event = self._event_for_result(request.operation, result)
        if result.succeeded:
            if request.operation in {
                FirewallOperation.ADD_RULE.value,
                FirewallOperation.DELETE_RULE.value,
            }:
                refresh, _rules = self._refresh_rules(f"{request.operation_id}:state")
                if not refresh.succeeded:
                    result = FirewallOperationResult(
                        **{
                            **result.__dict__,
                            "status": OperationStatus.VERIFICATION_FAILED.value,
                            "verified": False,
                            "error_code": "state_refresh_failed",
                            "message": "Alteração confirmada, mas o estado local não pôde ser atualizado.",
                        }
                    )
                    event = "verification_failed"
            elif isinstance(result.confirmed_state, dict):
                self.capability = FirewallCapability(
                    **{
                        **self.capability.__dict__,
                        "active": result.confirmed_state.get("active"),
                    }
                )
        if not self._audit(event, request, result=result, rule=rule):
            return FirewallOperationResult(
                **{
                    **result.__dict__,
                    "status": OperationStatus.AUDIT_FAILED.value,
                    "error_code": "audit_failed",
                    "message": "Estado alterado, mas o resultado não pôde ser auditado.",
                }
            )
        return result

    def _refresh_rules(self, operation_id):
        if not self.adapter or not hasattr(self.adapter, "list_rules"):
            return self._result(
                operation_id,
                OperationStatus.UNSUPPORTED,
                "rule_listing_unsupported",
                "Listagem de regras não suportada.",
            ), list(self._rules)
        result, rules = self.adapter.list_rules(operation_id)
        if result.succeeded:
            self._rules = list(rules)
            self._rules_loaded = True
        return result, list(self._rules)

    def _audit(self, event_type, request, result=None, rule=None):
        try:
            self.audit_repository.record(
                event_type,
                request,
                backend=self.capability.backend,
                result=result,
                rule=rule,
                action_origin="ui",
            )
            return True
        except Exception:
            return False

    def _safe_audit(self, event_type, request, result=None, rule=None):
        self._audit(event_type, request, result, rule)

    @staticmethod
    def _event_for_result(operation, result):
        if result.status == OperationStatus.SUCCESS.value:
            return {
                FirewallOperation.ADD_RULE.value: "rule_created",
                FirewallOperation.DELETE_RULE.value: "rule_removed",
                FirewallOperation.ENABLE.value: "firewall_enabled",
                FirewallOperation.DISABLE.value: "firewall_disabled",
            }.get(operation, "operation_completed")
        return {
            OperationStatus.CANCELLED.value: "privilege_cancelled",
            OperationStatus.DENIED.value: "privilege_denied",
            OperationStatus.VERIFICATION_FAILED.value: "verification_failed",
        }.get(result.status, "execution_failed")

    @staticmethod
    def _scope_for(request):
        if request.rule_id:
            return f"rule:{request.rule_id}"
        return f"firewall:{request.operation}"

    def _result(
        self,
        operation_id,
        status,
        error_code,
        message,
        requested_state=None,
    ):
        value = status.value if hasattr(status, "value") else str(status)
        return FirewallOperationResult(
            operation_id=str(operation_id),
            status=value,
            backend=self.capability.backend,
            requested_state=requested_state,
            changed=False,
            verified=False,
            error_code=error_code,
            message=message,
        )

    @staticmethod
    def _replace_operation_id(result, operation_id):
        return FirewallOperationResult(
            **{**result.__dict__, "operation_id": operation_id}
        )

    # Compatibilidade para consumidores legados. Novos fluxos usam execute().
    def get_status(self):
        request = FirewallOperationRequest.create(FirewallOperation.GET_STATUS)
        result = self.execute(request)
        if not result.succeeded:
            raise RuntimeError(result.message)
        return "active" if result.confirmed_state.get("active") else "inactive"

    def list_rules(self):
        request = FirewallOperationRequest.create(FirewallOperation.LIST_RULES)
        result = self.execute(request)
        return list(result.confirmed_state or ()) if result.succeeded else []
