import hashlib
import json
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5


class FirewallRule:
    """Contrato normalizado de uma regra confirmada pelo backend."""

    def __init__(
        self,
        name,
        port=None,
        protocol="tcp",
        action="deny",
        *,
        id=None,
        native_id=None,
        backend="unknown",
        platform="unknown",
        direction="in",
        source="any",
        destination="any",
        port_start=None,
        port_end=None,
        application=None,
        comment="",
        enabled=True,
        origin="user",
        protected=False,
        editable=True,
        created_at=None,
        updated_at=None,
        version=1,
        state_signature=None,
    ):
        # ``port`` mantém compatibilidade com FirewallRule(name, port, protocol, action).
        if port_start is None:
            port_start = port
        if port_end is None:
            port_end = port_start

        now = datetime.now(timezone.utc).isoformat()
        self.native_id = str(native_id) if native_id is not None else None
        self.backend = str(backend or "unknown").lower()
        self.platform = str(platform or "unknown")
        self.name = str(name or "").strip()
        self.action = str(action or "").lower()
        self.direction = str(direction or "in").lower()
        self.protocol = str(protocol or "tcp").lower()
        self.source = str(source or "any").lower()
        self.destination = str(destination or "any").lower()
        self.port_start = int(port_start) if port_start is not None else None
        self.port_end = int(port_end) if port_end is not None else self.port_start
        self.application = str(application) if application else None
        self.comment = str(comment or "")
        self.enabled = bool(enabled)
        self.origin = str(origin or "user").lower()
        self.protected = bool(protected)
        self.editable = bool(editable) and not self.protected
        self.created_at = str(created_at or now)
        self.updated_at = str(updated_at or now)
        self.version = max(1, int(version or 1))
        self.state_signature = state_signature or self.calculate_state_signature()
        stable_key = f"firewall:{self.backend}:{self.state_signature}"
        self.id = str(id or uuid5(NAMESPACE_URL, stable_key))

    @property
    def port(self):
        return self.port_start

    @port.setter
    def port(self, value):
        self.port_start = int(value)
        self.port_end = self.port_start
        self.refresh_signature()

    def normalized_state(self):
        return {
            "backend": self.backend,
            "platform": self.platform,
            "native_id": self.native_id,
            "name": self.name,
            "action": self.action,
            "direction": self.direction,
            "protocol": self.protocol,
            "source": self.source,
            "destination": self.destination,
            "port_start": self.port_start,
            "port_end": self.port_end,
            "application": self.application,
            "comment": self.comment,
            "enabled": self.enabled,
            "origin": self.origin,
            "protected": self.protected,
            "editable": self.editable,
        }

    def calculate_state_signature(self):
        state = self.normalized_state()
        # A numeração do UFW muda quando regras anteriores são removidas; ela
        # identifica a operação nativa, mas não faz parte da identidade semântica.
        state.pop("native_id", None)
        payload = json.dumps(
            state,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def refresh_signature(self):
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.version += 1
        self.state_signature = self.calculate_state_signature()
        return self.state_signature

    def to_dict(self):
        data = self.normalized_state()
        data.update({
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "state_signature": self.state_signature,
            "comment": self.comment,
        })
        return data

    def __str__(self):
        port = (
            str(self.port_start)
            if self.port_start == self.port_end
            else f"{self.port_start}-{self.port_end}"
        )
        return (
            f"Regra: {self.name} | Porta: {port} | Protocolo: "
            f"{self.protocol} | Ação: {self.action}"
        )
