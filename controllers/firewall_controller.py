from datetime import datetime

from models.firewall_rule import FirewallRule
from models.permission_model import Permission
from models.wifi_model import WiFi

from services.firewall_service import FirewallService
from core.platform.platform_factory import PlatformFactory


class FirewallController:
    """
    Controller do firewall.

    Responsável por:
    - coordenar regras
    - permissões de aplicativos
    - redes Wi-Fi
    - comunicação com FirewallService
    """

    MAX_LOGS = 500

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):

        self.firewall_service = FirewallService()

        # adapter multiplataforma
        self.adapter = PlatformFactory.create()

        self.rules = []
        self.permissions = []
        self.wifi_networks = []
        self.logs = []

    # =====================================================
    # PERMISSÕES DE APLICATIVOS
    # =====================================================

    def add_permission(self, app_name, allow_traffic):

        if not app_name:
            return

        app_name = app_name.strip()

        permission = next(
            (p for p in self.permissions
             if p.app_name.lower() == app_name.lower()),
            None
        )

        if permission:
            permission.allow_traffic = allow_traffic

        else:
            self.permissions.append(
                Permission(app_name, allow_traffic)
            )

        self.log_action(
            f"Permissão {'permitida' if allow_traffic else 'bloqueada'} para {app_name}"
        )

    def remove_permission(self, app_name):

        if not app_name:
            return

        self.permissions = [
            p for p in self.permissions
            if p.app_name.lower() != app_name.lower()
        ]

        self.log_action(f"Permissão removida para {app_name}")

    def get_permissions(self):

        return [
            f"{p.app_name} - {'Permitido' if p.allow_traffic else 'Bloqueado'}"
            for p in self.permissions
        ]

    def notify_impact(self, app_name):

        permission = next(
            (p for p in self.permissions
             if p.app_name.lower() == app_name.lower()),
            None
        )

        if permission and not permission.allow_traffic:
            return f"⚠ Aviso: Interromper {app_name} pode causar lentidão!"

        return ""

    # =====================================================
    # REDES WIFI
    # =====================================================

    def scan_wifi_networks(self):
        """
        Escaneia redes Wi-Fi usando o adapter do sistema.
        """

        try:
            return self.adapter.scan_wifi_networks()
        except Exception:
            return []

    def add_wifi_network(self, ssid, allow_traffic):

        if not ssid:
            return

        ssid = ssid.strip()

        wifi = next(
            (w for w in self.wifi_networks
             if w.ssid.lower() == ssid.lower()),
            None
        )

        if wifi:
            wifi.allow_traffic = allow_traffic

        else:
            self.wifi_networks.append(
                WiFi(ssid, allow_traffic)
            )

        self.log_action(
            f"Wi-Fi {'permitido' if allow_traffic else 'bloqueado'}: {ssid}"
        )

    def remove_wifi_network(self, ssid):

        if not ssid:
            return

        self.wifi_networks = [
            w for w in self.wifi_networks
            if w.ssid.lower() != ssid.lower()
        ]

        self.log_action(f"Wi-Fi removido: {ssid}")

    def get_wifi_networks(self):

        return [
            f"{w.ssid} - {'Permitido' if w.allow_traffic else 'Bloqueado'}"
            for w in self.wifi_networks
        ]

    # =====================================================
    # STATUS DO FIREWALL
    # =====================================================

    def get_firewall_status(self):

        try:

            status = self.firewall_service.get_status()

            if not status:
                return "Status desconhecido"

            status_lower = status.lower()

            if "active" in status_lower or "enabled" in status_lower:
                return "Ativado"

            if "inactive" in status_lower or "disabled" in status_lower:
                return "Desativado"

            return status

        except Exception as e:

            return f"Erro ao verificar status do firewall: {e}"

    # =====================================================
    # REGRAS
    # =====================================================

    def add_rule(self, name, port, protocol, action):

        if not name:
            return

        existing_rule = next(
            (r for r in self.rules if r.name.lower() == name.lower()),
            None
        )

        if existing_rule:
            return

        rule = FirewallRule(name, port, protocol, action)

        self.rules.append(rule)

        try:

            if action == "allow":
                self.firewall_service.allow_port(port)

            elif action in ("block", "deny"):
                self.firewall_service.block_port(port)

        except Exception:
            pass

        self.log_action(
            f"Regra adicionada: {name} ({action} - Porta {port})"
        )

    def remove_rule(self, name):

        rule = next(
            (r for r in self.rules if r.name.lower() == name.lower()),
            None
        )

        if rule:

            self.rules.remove(rule)

            try:
                self.firewall_service.remove_rule(name)
            except Exception:
                pass

            self.log_action(f"Regra removida: {name}")

            return f"✅ Regra '{name}' removida com sucesso!"

        return f"⚠ Regra '{name}' não encontrada"

    def list_rules(self):

        if not self.rules:
            return ["Nenhuma regra ativa."]

        return [str(r) for r in self.rules]

    # =====================================================
    # CONTROLE DO FIREWALL
    # =====================================================

    def activate_firewall(self):

        try:

            message = self.firewall_service.activate()

            self.log_action("Firewall ativado")

            return f"✅ {message}"

        except Exception as e:

            return f"❌ Erro ao ativar firewall: {e}"

    def deactivate_firewall(self):

        try:

            message = self.firewall_service.deactivate()

            self.log_action("Firewall desativado")

            return f"✅ {message}"

        except Exception as e:

            return f"❌ Erro ao desativar firewall: {e}"

    # =====================================================
    # MONITORAMENTO DE REDE
    # =====================================================

    def start_monitoring(self):

        try:

            self.firewall_service.start_monitoring()

            self.log_action("Monitoramento de rede iniciado")

        except Exception:
            pass

    def stop_monitoring(self):

        try:

            self.firewall_service.stop_monitoring()

            self.log_action("Monitoramento de rede parado")

        except Exception:
            pass

    def get_connections(self):

        try:
            return self.firewall_service.get_connections()
        except Exception:
            return []

    # =====================================================
    # LOG
    # =====================================================

    def log_action(self, action):

        timestamp = datetime.now().strftime("%H:%M:%S")

        self.logs.append(f"[{timestamp}] {action}")

        if len(self.logs) > self.MAX_LOGS:
            self.logs.pop(0)

    def get_logs(self):

        return list(self.logs)
