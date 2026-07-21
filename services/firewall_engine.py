from models.firewall_contracts import FirewallOperation, FirewallOperationRequest
from services.firewall_service import FirewallService


class FirewallEngine:
    """Compatibilidade legada delegada ao fluxo auditado e pós-verificado."""

    def __init__(self, engine_type, firewall_service=None):
        self.engine_type = str(engine_type)
        self.firewall_service = firewall_service or FirewallService()

    def _ensure_supported(self):
        if self.engine_type != "ufw":
            raise RuntimeError("Engine de firewall não suportada")

    @staticmethod
    def _require_success(result):
        if not result.succeeded:
            raise RuntimeError(result.message or "Operação de Firewall não confirmada")
        return result

    def _execute(self, operation, payload=None):
        self._ensure_supported()
        request = FirewallOperationRequest.create(
            operation,
            payload=payload,
            reason="Compatibilidade com FirewallEngine.",
        )
        return self._require_success(self.firewall_service.execute(request))

    def status(self):
        result = self._execute(FirewallOperation.GET_STATUS)
        return "active" if result.confirmed_state.get("active") else "inactive"

    def enable(self):
        self._execute(FirewallOperation.ENABLE)
        return "Firewall ativado e confirmado"

    def disable(self):
        self._execute(FirewallOperation.DISABLE)
        return "Firewall desativado e confirmado"

    def allow_port(self, port):
        self._port_rule(port, "allow")
        return f"Porta {int(port)} liberada e confirmada"

    def block_port(self, port):
        self._port_rule(port, "deny")
        return f"Porta {int(port)} bloqueada e confirmada"

    def _port_rule(self, port, action):
        return self._execute(
            FirewallOperation.ADD_RULE,
            {
                "name": f"Compatibilidade {action} porta {port}",
                "port": port,
                "protocol": "tcp",
                "action": action,
                "direction": "in",
                "source": "any",
                "destination": "any",
            },
        )
