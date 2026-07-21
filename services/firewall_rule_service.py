from models.firewall_contracts import FirewallOperation, FirewallOperationRequest
from services.firewall_service import FirewallService


class FirewallRuleService:
    """Fachada legada sem estado próprio; a fonte única é FirewallService."""

    def __init__(self, firewall_service=None):
        self.firewall_service = firewall_service or FirewallService()

    @property
    def rules(self):
        return list(self.firewall_service.snapshot_rules())

    def add_rule(self, name, port, protocol, action):
        request = FirewallOperationRequest.create(
            FirewallOperation.ADD_RULE,
            payload={
                "name": name,
                "port": port,
                "protocol": protocol,
                "action": "deny" if action == "block" else action,
                "direction": "in",
                "source": "any",
                "destination": "any",
            },
            reason="Compatibilidade com FirewallRuleService.",
        )
        return self.firewall_service.execute(request)

    def remove_rule(self, rule_id, expected_version=None):
        if expected_version is None:
            raise ValueError(
                "expected_version é obrigatório; remoção aproximada por nome foi desabilitada."
            )
        request = FirewallOperationRequest.create(
            FirewallOperation.DELETE_RULE,
            rule_id=rule_id,
            expected_version=expected_version,
            reason="Compatibilidade com FirewallRuleService.",
        )
        return self.firewall_service.execute(request)

    def list_rules(self):
        request = FirewallOperationRequest.create(FirewallOperation.LIST_RULES)
        result = self.firewall_service.execute(request)
        return list(result.confirmed_state or ()) if result.succeeded else []
