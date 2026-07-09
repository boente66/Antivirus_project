from services.firewall_detector import FirewallDetector
from services.firewall_engine import FirewallEngine
from services.firewall_rule_service import FirewallRuleService
from services.firewall_monitor_service import FirewallMonitorService


class FirewallService:
    """
    Serviço central do firewall.

    Responsável por:
    - detectar engine do firewall
    - aplicar regras
    - controlar firewall
    - monitorar conexões
    """

    def __init__(self):

        # -------------------------------------
        # Detectar firewall do sistema
        # -------------------------------------
        self.detector = FirewallDetector()

        self.engine_type = self.detector.detect()

        # -------------------------------------
        # Engine real do firewall
        # -------------------------------------
        self.engine = FirewallEngine(self.engine_type)

        # -------------------------------------
        # Regras internas do aplicativo
        # -------------------------------------
        self.rule_service = FirewallRuleService()

        # -------------------------------------
        # Monitor de conexões
        # -------------------------------------
        self.monitor_service = FirewallMonitorService()

    # =========================================
    # STATUS
    # =========================================

    def get_status(self):

        return self.engine.status()

    # =========================================
    # CONTROLE DO FIREWALL
    # =========================================

    def activate_firewall(self):

        return self.engine.enable()

    def deactivate_firewall(self):

        return self.engine.disable()

    # Backwards-compatible aliases expected by some callers
    def activate(self):
        """
        Alias for activate_firewall to maintain backward compatibility.
        """
        return self.activate_firewall()

    def deactivate(self):
        """
        Alias for deactivate_firewall to maintain backward compatibility.
        """
        return self.deactivate_firewall()

    # =========================================
    # REGRAS
    # =========================================

    def allow_port(self, port):

        self.rule_service.add_rule(
            name=f"Allow Port {port}",
            port=port,
            protocol="tcp",
            action="allow"
        )

        return self.engine.allow_port(port)

    def block_port(self, port):

        self.rule_service.add_rule(
            name=f"Block Port {port}",
            port=port,
            protocol="tcp",
            action="deny"
        )

        return self.engine.block_port(port)

    def list_rules(self):

        return self.rule_service.list_rules()

    def remove_rule(self, name):

        self.rule_service.remove_rule(name)

    # =========================================
    # MONITORAMENTO
    # =========================================

    def start_monitoring(self):

        self.monitor_service.start()

    def stop_monitoring(self):

        self.monitor_service.stop()

    def get_connections(self):

        return self.monitor_service.get_connections()
    
