from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class FirewallOperation(str, Enum):
    DETECT_CAPABILITY = "detect_capability"
    GET_STATUS = "get_status"
    LIST_RULES = "list_rules"
    ENABLE = "enable"
    DISABLE = "disable"
    ADD_RULE = "add_rule"
    DELETE_RULE = "delete_rule"


class OperationStatus(str, Enum):
    SUCCESS = "success"
    CANCELLED = "cancelled"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    EXECUTION_FAILED = "execution_failed"
    VERIFICATION_FAILED = "verification_failed"
    UNSUPPORTED = "unsupported"
    BACKEND_CONFLICT = "backend_conflict"
    TIMED_OUT = "timed_out"
    INVALID_REQUEST = "invalid_request"
    CONFLICT = "conflict"
    BUSY = "busy"
    AUDIT_FAILED = "audit_failed"


class SupportStatus(str, Enum):
    SUPPORTED = "supported"
    READ_ONLY = "read_only"
    UNSUPPORTED = "unsupported"
    BACKEND_CONFLICT = "backend_conflict"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class FirewallCapability:
    platform: str
    backend: str
    installed: bool
    active: Optional[bool]
    readable: bool
    writable: bool
    requires_privilege: bool
    support_status: str
    reason: str = ""

    @property
    def write_blocked(self):
        return not self.writable or self.support_status != SupportStatus.SUPPORTED.value


@dataclass(frozen=True)
class PrivilegeRequirement:
    required: bool
    operation: str
    reason: str
    scope: str
    backend: str
    can_prompt: bool


@dataclass(frozen=True)
class PrivilegeResult:
    status: str
    granted: bool = False
    cancelled: bool = False
    denied: bool = False
    unavailable: bool = False
    timed_out: bool = False
    message: str = ""
    technical_details: str = ""


@dataclass(frozen=True)
class FirewallOperationRequest:
    operation_id: str
    operation: str
    rule_id: Optional[str] = None
    expected_version: Optional[int] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    requested_by: str = "user"
    reason: str = ""

    @classmethod
    def create(
        cls,
        operation,
        rule_id=None,
        expected_version=None,
        payload=None,
        requested_by="user",
        reason="",
    ):
        value = operation.value if isinstance(operation, Enum) else str(operation)
        return cls(
            operation_id=str(uuid4()),
            operation=value,
            rule_id=rule_id,
            expected_version=expected_version,
            payload=dict(payload or {}),
            requested_by=str(requested_by or "user"),
            reason=str(reason or ""),
        )


@dataclass(frozen=True)
class FirewallOperationResult:
    operation_id: str
    status: str
    backend: str
    requested_state: Any = None
    confirmed_state: Any = None
    changed: bool = False
    verified: bool = False
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_code: Optional[str] = None
    message: str = ""

    @property
    def succeeded(self):
        return self.status == OperationStatus.SUCCESS.value and self.verified


@dataclass(frozen=True)
class FirewallCommandResult:
    status: str
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_code: Optional[str] = None
    message: str = ""
    privilege: Optional[PrivilegeResult] = None

    @property
    def succeeded(self):
        return self.status == OperationStatus.SUCCESS.value
