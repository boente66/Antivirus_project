import getpass
import json
import re
from datetime import datetime, timezone

from database.database import Database
from database.entity.firewall_audit_entity import FirewallAuditEntity


class FirewallAuditRepository(Database):
    SENSITIVE_MARKERS = ("password", "passwd", "secret", "token", "credential")

    def record(
        self,
        event_type,
        request,
        *,
        backend="unknown",
        result=None,
        rule=None,
        message="",
        action_origin="ui",
    ):
        safe_payload = self._redact(getattr(request, "payload", None))
        requested_state = (
            getattr(result, "requested_state", None) if result else safe_payload
        )
        confirmed_state = getattr(result, "confirmed_state", None) if result else None
        entity = FirewallAuditEntity(
            operation_id=str(getattr(request, "operation_id", "unknown")),
            timestamp=datetime.now(timezone.utc).isoformat(),
            system_user=self._system_user(),
            event_type=str(event_type),
            operation=str(getattr(request, "operation", "unknown")),
            backend=str(backend or "unknown"),
            rule_data=self._json(self._redact(rule.to_dict() if rule else None)),
            requested_state=self._json(self._redact(requested_state)),
            confirmed_state=self._json(self._redact(confirmed_state)),
            result=str(getattr(result, "status", "requested")),
            exit_code=getattr(result, "exit_code", None),
            error_code=getattr(result, "error_code", None),
            message=self._redact_text(
                str(message or getattr(result, "message", "") or "")
            ),
            action_origin=str(action_origin or "ui"),
        )
        with self.operation_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO firewall_audit (
                    operation_id, timestamp, system_user, event_type,
                    operation, backend, rule_data, requested_state,
                    confirmed_state, result, exit_code, error_code,
                    message, action_origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                entity.to_tuple(),
            )
            entity.id = cursor.lastrowid
        return entity.id

    def list_by_operation(self, operation_id):
        with self.operation_connection() as conn:
            return conn.execute(
                "SELECT * FROM firewall_audit WHERE operation_id = ? "
                "ORDER BY id ASC",
                (str(operation_id),),
            ).fetchall()

    @classmethod
    def _redact(cls, value):
        if isinstance(value, dict):
            cleaned = {}
            for key, item in value.items():
                lowered = str(key).lower()
                cleaned[str(key)] = (
                    "[REDACTED]"
                    if any(marker in lowered for marker in cls.SENSITIVE_MARKERS)
                    else cls._redact(item)
                )
            return cleaned
        if isinstance(value, (list, tuple)):
            return [cls._redact(item) for item in value]
        return value

    @staticmethod
    def _json(value):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

    @classmethod
    def _redact_text(cls, value):
        markers = "|".join(re.escape(marker) for marker in cls.SENSITIVE_MARKERS)
        return re.sub(
            rf"(?i)\b({markers})\b\s*[:=]\s*([^\s,;]+)",
            r"\1=[REDACTED]",
            str(value or ""),
        )

    @staticmethod
    def _system_user():
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"
