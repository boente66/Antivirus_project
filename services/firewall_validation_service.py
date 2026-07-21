import ipaddress
import re

from models.firewall_rule import FirewallRule


class FirewallValidationError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.code = f"invalid_{field}"


class FirewallValidationService:
    SAFE_TEXT = re.compile(r"^[\w .:/()\-]{1,80}$", re.UNICODE)
    SUPPORTED_ACTIONS = {"allow", "deny"}
    SUPPORTED_DIRECTIONS = {"in", "out"}
    SUPPORTED_PROTOCOLS = {"tcp", "udp"}
    SAFE_APPLICATION = re.compile(r"^[\w .()+@_-]{1,80}$", re.UNICODE)

    def normalize_rule(self, payload, backend="ufw", platform="Linux"):
        payload = dict(payload or {})
        name = self._safe_text(payload.get("name"), "name", required=True)
        action = self._choice(payload.get("action"), "action", self.SUPPORTED_ACTIONS)
        direction = self._choice(
            payload.get("direction", "in"),
            "direction",
            self.SUPPORTED_DIRECTIONS,
        )
        application = self._application(payload.get("application"))
        if application:
            return FirewallRule(
                name=name,
                protocol="any",
                action=action,
                backend=backend,
                platform=platform,
                direction=direction,
                source="any",
                destination="any",
                port_start=None,
                port_end=None,
                application=application,
                comment=self._safe_text(
                    payload.get("comment", ""), "comment", required=False
                ),
                origin=str(payload.get("origin") or "user").lower(),
                protected=bool(payload.get("protected", False)),
                editable=bool(payload.get("editable", True)),
            )
        protocol = self._choice(
            payload.get("protocol"),
            "protocol",
            self.SUPPORTED_PROTOCOLS,
        )
        port_start, port_end = self._ports(payload)
        source = self._network(payload.get("source", "any"), "source")
        destination = self._network(
            payload.get("destination", "any"), "destination"
        )
        comment = self._safe_text(
            payload.get("comment", ""), "comment", required=False
        )

        return FirewallRule(
            name=name,
            protocol=protocol,
            action=action,
            backend=backend,
            platform=platform,
            direction=direction,
            source=source,
            destination=destination,
            port_start=port_start,
            port_end=port_end,
            application=None,
            comment=comment,
            origin=str(payload.get("origin") or "user").lower(),
            protected=bool(payload.get("protected", False)),
            editable=bool(payload.get("editable", True)),
        )

    def _application(self, value):
        text = str(value or "").strip()
        if not text:
            return None
        if not self.SAFE_APPLICATION.fullmatch(text):
            raise FirewallValidationError(
                "application",
                "Perfil de aplicação UFW inválido ou não permitido.",
            )
        return text

    def _ports(self, payload):
        start = payload.get("port_start", payload.get("port"))
        end = payload.get("port_end", start)
        if isinstance(start, bool) or isinstance(end, bool):
            raise FirewallValidationError("port", "Porta deve ser um inteiro.")
        try:
            start = int(start)
            end = int(end)
        except (TypeError, ValueError):
            raise FirewallValidationError(
                "port", "Porta e faixa devem conter somente números inteiros."
            )
        if not 1 <= start <= 65535 or not 1 <= end <= 65535:
            raise FirewallValidationError(
                "port", "Portas devem estar entre 1 e 65535."
            )
        if start > end:
            raise FirewallValidationError(
                "port_range", "A porta inicial não pode ser maior que a final."
            )
        return start, end

    def _choice(self, value, field, accepted):
        normalized = str(value or "").strip().lower()
        if normalized not in accepted:
            allowed = ", ".join(sorted(accepted))
            raise FirewallValidationError(
                field, f"Valor inválido para {field}. Permitidos: {allowed}."
            )
        return normalized

    def _network(self, value, field):
        text = str(value or "any").strip().lower()
        if text in {"any", "anywhere"}:
            return "any"
        if any(char in text for char in (";", "`", "$", "\n", "\r", "\x00")):
            raise FirewallValidationError(field, f"{field} contém caracteres inválidos.")
        try:
            if "/" in text:
                network = ipaddress.ip_network(text, strict=False)
                if network.prefixlen == network.max_prefixlen:
                    return str(network.network_address)
                return str(network)
            return str(ipaddress.ip_address(text))
        except ValueError as exc:
            raise FirewallValidationError(
                field, f"Endereço IPv4, IPv6 ou CIDR inválido em {field}."
            ) from exc

    def _safe_text(self, value, field, required):
        text = str(value or "").strip()
        if not text and not required:
            return ""
        if not text or not self.SAFE_TEXT.fullmatch(text):
            raise FirewallValidationError(
                field,
                f"{field} contém caracteres não permitidos ou excede 80 caracteres.",
            )
        return text
