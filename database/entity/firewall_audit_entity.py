from dataclasses import dataclass
from typing import Optional


@dataclass
class FirewallAuditEntity:
    operation_id: str
    timestamp: str
    system_user: str
    event_type: str
    operation: str
    backend: str
    rule_data: Optional[str]
    requested_state: Optional[str]
    confirmed_state: Optional[str]
    result: str
    exit_code: Optional[int]
    error_code: Optional[str]
    message: str
    action_origin: str
    id: Optional[int] = None

    def to_tuple(self):
        return (
            self.operation_id,
            self.timestamp,
            self.system_user,
            self.event_type,
            self.operation,
            self.backend,
            self.rule_data,
            self.requested_state,
            self.confirmed_state,
            self.result,
            self.exit_code,
            self.error_code,
            self.message,
            self.action_origin,
        )
