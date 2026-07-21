import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from controllers.firewall_controller import FirewallController
from core.platform.linux_adapter import LinuxAdapter
from core.platform.mac_adapter import MacAdapter
from core.platform.platform_factory import PlatformFactory
from core.platform.windows_adapter import WindowsAdapter
from database.repositories.firewall_audit_repository import FirewallAuditRepository
from models.firewall_contracts import (
    FirewallCapability,
    FirewallCommandResult,
    FirewallOperation,
    FirewallOperationRequest,
    FirewallOperationResult,
    OperationStatus,
    SupportStatus,
)
from models.firewall_rule import FirewallRule
from services.firewall_admin_executor import (
    FirewallAdminExecutor,
    FirewallAdminOperation,
)
from services.firewall_detector import FirewallDetector
from services.firewall_service import FirewallService
from services.firewall_validation_service import (
    FirewallValidationError,
    FirewallValidationService,
)
from views.firewall_view import FirewallView


ACTIVE_EMPTY = "Status: active\n\nTo  Action  From\n"
INACTIVE = "Status: inactive\n"
RULE_UDP = (
    "Status: active\n\n"
    "[ 1] 5353/udp                  DENY IN     Anywhere                   # DNS teste\n"
)


def completed(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def command_result(status=OperationStatus.SUCCESS, stdout="", stderr="", code=0, error=None):
    value = status.value if hasattr(status, "value") else status
    return FirewallCommandResult(
        status=value,
        exit_code=code,
        stdout=stdout,
        stderr=stderr,
        error_code=error,
        message="ok" if value == OperationStatus.SUCCESS.value else "falhou",
    )


def operation_result(operation_id, status=OperationStatus.SUCCESS, **kwargs):
    value = status.value if hasattr(status, "value") else status
    verified = kwargs.pop("verified", value == OperationStatus.SUCCESS.value)
    message = kwargs.pop("message", "resultado")
    return FirewallOperationResult(
        operation_id=operation_id,
        status=value,
        backend="ufw",
        verified=verified,
        message=message,
        **kwargs,
    )


def linux_capability(active=True, writable=True):
    return FirewallCapability(
        platform="Linux",
        backend="ufw",
        installed=True,
        active=active,
        readable=True,
        writable=writable,
        requires_privilege=True,
        support_status=(
            SupportStatus.SUPPORTED.value if writable else SupportStatus.READ_ONLY.value
        ),
        reason="UFW validado.",
    )


class StaticDetector:
    def __init__(self, capability):
        self.capability = capability

    def detect_capability(self):
        return self.capability


class MemoryAudit:
    def __init__(self, fail=False):
        self.events = []
        self.fail = fail

    def record(self, event_type, request, **kwargs):
        if self.fail:
            raise RuntimeError("audit unavailable")
        self.events.append((event_type, request.operation_id, kwargs))
        return len(self.events)


class MemoryAdapter:
    backend = "ufw"

    def __init__(self, rules=None):
        self.rules = list(rules or [])
        self.add_result = None
        self.delete_result = None
        self.enable_gate = None

    @staticmethod
    def rules_match(left, right):
        return LinuxAdapter.rules_match(left, right)

    def read_status(self, operation_id):
        return operation_result(operation_id, confirmed_state={"active": True})

    def list_rules(self, operation_id):
        return operation_result(
            operation_id, confirmed_state={"active": True, "rule_count": len(self.rules)}
        ), list(self.rules)

    def add_rule(self, operation_id, rule):
        if self.add_result is not None:
            return self.add_result
        confirmed = FirewallRule(**rule.to_dict())
        confirmed.native_id = str(len(self.rules) + 1)
        self.rules.append(confirmed)
        return operation_result(
            operation_id,
            requested_state=rule.to_dict(),
            confirmed_state=confirmed.to_dict(),
            changed=True,
        )

    def delete_rule(self, operation_id, rule):
        if self.delete_result is not None:
            return self.delete_result
        self.rules = [item for item in self.rules if item.id != rule.id]
        return operation_result(
            operation_id,
            requested_state=rule.to_dict(),
            confirmed_state={"absent": True},
            changed=True,
        )

    def enable(self, operation_id):
        if self.enable_gate:
            self.enable_gate[0].set()
            self.enable_gate[1].wait(2)
        return operation_result(
            operation_id, confirmed_state={"active": True}, changed=True
        )

    def disable(self, operation_id):
        return operation_result(
            operation_id, confirmed_state={"active": False}, changed=True
        )


class FirewallDetectionTests(unittest.TestCase):
    @staticmethod
    def _which(mapping):
        return lambda name: mapping.get(name)

    @staticmethod
    def _runner_for(ufw_output):
        def runner(command, **_kwargs):
            executable = Path(command[0]).name
            if executable == "ufw":
                return completed(stdout=ufw_output)
            if executable == "firewall-cmd":
                return completed(returncode=1, stdout="not running")
            return completed(stdout="")
        return runner

    def test_ufw_absent(self):
        detector = FirewallDetector(
            system_name=lambda: "Linux", which=self._which({}), runner=lambda *_a, **_k: completed()
        )
        capability = detector.detect_capability()
        self.assertFalse(capability.installed)
        self.assertFalse(capability.writable)
        self.assertEqual(capability.support_status, SupportStatus.UNSUPPORTED.value)

    def test_ufw_installed_inactive(self):
        mapping = {"ufw": "/usr/sbin/ufw", "pkexec": "/usr/bin/pkexec"}
        capability = FirewallDetector(
            system_name=lambda: "Linux",
            which=self._which(mapping),
            runner=self._runner_for(INACTIVE),
        ).detect_capability()
        self.assertFalse(capability.active)
        self.assertTrue(capability.writable)

    def test_ufw_status_is_deferred_to_authorized_read(self):
        mapping = {"ufw": "/usr/sbin/ufw", "pkexec": "/usr/bin/pkexec"}
        capability = FirewallDetector(
            system_name=lambda: "Linux",
            which=self._which(mapping),
            runner=self._runner_for(ACTIVE_EMPTY),
        ).detect_capability()
        self.assertIsNone(capability.active)
        self.assertTrue(capability.readable)
        self.assertEqual(capability.support_status, SupportStatus.SUPPORTED.value)

    def test_detection_does_not_run_ufw_status_without_authorization(self):
        mapping = {"ufw": "/usr/sbin/ufw", "pkexec": "/usr/bin/pkexec"}

        def runner(command, **_kwargs):
            if Path(command[0]).name == "ufw":
                return completed(returncode=1, stderr="permission denied")
            return completed(stdout="")

        capability = FirewallDetector(
            system_name=lambda: "Linux", which=self._which(mapping), runner=runner
        ).detect_capability()
        self.assertTrue(capability.installed)
        self.assertTrue(capability.readable)
        self.assertTrue(capability.writable)
        self.assertIsNone(capability.active)
        self.assertEqual(capability.support_status, SupportStatus.SUPPORTED.value)

    def test_backend_ambiguous_blocks_write(self):
        mapping = {
            "ufw": "/usr/sbin/ufw",
            "pkexec": "/usr/bin/pkexec",
            "firewall-cmd": "/usr/bin/firewall-cmd",
        }

        def runner(command, **_kwargs):
            name = Path(command[0]).name
            if name == "firewall-cmd":
                return completed(stdout="running")
            return completed(stdout=ACTIVE_EMPTY)

        capability = FirewallDetector(
            system_name=lambda: "Linux", which=self._which(mapping), runner=runner
        ).detect_capability()
        self.assertEqual(capability.support_status, SupportStatus.BACKEND_CONFLICT.value)
        self.assertFalse(capability.writable)

    def test_windows_and_macos_writes_are_unsupported(self):
        windows = FirewallDetector(
            system_name=lambda: "Windows",
            which=self._which({"powershell.exe": "C:/Windows/System32/powershell.exe"}),
            runner=lambda *_args, **_kwargs: completed(stdout="True\nTrue\nTrue\n"),
        ).detect_capability()
        macos = FirewallDetector(system_name=lambda: "Darwin").detect_capability()
        self.assertTrue(windows.write_blocked)
        self.assertEqual(windows.support_status, SupportStatus.READ_ONLY.value)
        self.assertTrue(windows.readable)
        self.assertTrue(windows.active)
        self.assertTrue(macos.write_blocked)
        self.assertEqual(macos.support_status, SupportStatus.UNSUPPORTED.value)

    def test_linux_platform_adapter_delegates_firewall_status(self):
        executor = SequenceExecutor([command_result(stdout=ACTIVE_EMPTY)])
        adapter = LinuxAdapter(firewall_executor=executor)
        self.assertEqual(adapter.get_firewall_status(), "active")
        self.assertEqual(executor.calls[0][0], FirewallAdminOperation.UFW_STATUS)

    def test_detector_obtains_backend_through_platform_adapter(self):
        class Platform:
            def __init__(self):
                self.called = False

            def detect_firewall_capability(self, **dependencies):
                self.called = dependencies.get("executor") is not None
                return linux_capability()

        platform_adapter = Platform()
        mapping = {"ufw": "/usr/sbin/ufw", "pkexec": "/usr/bin/pkexec"}
        capability = FirewallDetector(
            system_name=lambda: "Linux",
            which=self._which(mapping),
            runner=self._runner_for(ACTIVE_EMPTY),
            platform_adapter=platform_adapter,
        ).detect_capability()
        self.assertTrue(platform_adapter.called)
        self.assertTrue(capability.active)

    def test_factory_maps_each_supported_operating_system(self):
        self.assertIsInstance(PlatformFactory.create_for("Linux"), LinuxAdapter)
        self.assertIsInstance(PlatformFactory.create_for("Windows"), WindowsAdapter)
        self.assertIsInstance(PlatformFactory.create_for("Darwin"), MacAdapter)
        self.assertIsInstance(PlatformFactory.create_for("macOS"), MacAdapter)

    def test_injected_adapter_is_the_authority_for_platform_identity(self):
        capability = FirewallDetector(
            system_name=lambda: "Linux",
            platform_adapter=MacAdapter(),
        ).detect_capability()
        self.assertEqual(capability.platform, "macOS")
        self.assertEqual(capability.backend, "macos_firewall")


class AdminExecutorTests(unittest.TestCase):
    PATHS = {"ufw": "/usr/sbin/ufw", "pkexec": "/usr/bin/pkexec"}

    def _execute(self, result=None, error=None, paths=None, operation=FirewallAdminOperation.UFW_ENABLE):
        def runner(*_args, **_kwargs):
            if error:
                raise error
            return result or completed(stdout="ok")

        executor = FirewallAdminExecutor(
            runner=runner,
            which=lambda name: (paths or self.PATHS).get(name),
        )
        return executor.execute(operation)

    def test_authorization_granted(self):
        result = self._execute()
        self.assertTrue(result.succeeded)
        self.assertTrue(result.privilege.granted)

    def test_authorization_cancelled(self):
        result = self._execute(completed(126, stderr="dismissed by user"))
        self.assertEqual(result.status, OperationStatus.CANCELLED.value)

    def test_authorization_denied(self):
        result = self._execute(completed(127, stderr="not authorized"))
        self.assertEqual(result.status, OperationStatus.DENIED.value)

    def test_pkexec_absent(self):
        result = self._execute(paths={"ufw": "/usr/sbin/ufw"})
        self.assertEqual(result.error_code, "pkexec_not_found")

    def test_polkit_agent_absent(self):
        result = self._execute(completed(1, stderr="No authentication agent found"))
        self.assertEqual(result.error_code, "polkit_agent_unavailable")

    def test_timeout(self):
        result = self._execute(error=subprocess.TimeoutExpired("ufw", 1))
        self.assertEqual(result.status, OperationStatus.TIMED_OUT.value)

    def test_nonzero_exit(self):
        result = self._execute(completed(2, stderr="backend failed"))
        self.assertEqual(result.error_code, "backend_exit_nonzero")

    def test_stderr_with_zero_exit_is_failure(self):
        result = self._execute(completed(0, stderr="unexpected warning"))
        self.assertEqual(result.error_code, "backend_stderr")

    def test_arbitrary_operation_is_rejected(self):
        executor = FirewallAdminExecutor(which=lambda name: self.PATHS.get(name))
        result = executor.execute("RUN_ANYTHING", ("--force",))
        self.assertEqual(result.error_code, "operation_not_allowlisted")

    def test_argument_structure_is_strict(self):
        executor = FirewallAdminExecutor(which=lambda name: self.PATHS.get(name))
        result = executor.execute(
            FirewallAdminOperation.UFW_ADD_RULE,
            ("deny", "in", "from", "any", "proto", "tcp", "to", "any", "port", "80"),
        )
        self.assertEqual(result.error_code, "arguments_rejected")


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.validation = FirewallValidationService()
        self.valid = {
            "name": "Teste seguro",
            "action": "deny",
            "direction": "in",
            "protocol": "udp",
            "port_start": 1000,
            "port_end": 2000,
            "source": "2001:db8::/64",
            "destination": "192.0.2.0/24",
        }

    def assert_invalid(self, field, value, expected_field):
        payload = dict(self.valid)
        payload[field] = value
        with self.assertRaises(FirewallValidationError) as caught:
            self.validation.normalize_rule(payload)
        self.assertEqual(caught.exception.field, expected_field)

    def test_protocol_and_networks_are_preserved(self):
        rule = self.validation.normalize_rule(self.valid)
        self.assertEqual(rule.protocol, "udp")
        self.assertEqual(rule.source, "2001:db8::/64")
        self.assertEqual(rule.destination, "192.0.2.0/24")
        args = LinuxAdapter().build_firewall_add_arguments(rule)
        self.assertEqual(args[3], "udp")

    def test_invalid_port(self):
        self.assert_invalid("port_start", 0, "port")

    def test_invalid_range(self):
        self.assert_invalid("port_start", 3000, "port_range")

    def test_invalid_ipv4(self):
        self.assert_invalid("destination", "999.1.1.1", "destination")

    def test_invalid_ipv6(self):
        self.assert_invalid("source", "2001:::1", "source")

    def test_invalid_cidr(self):
        self.assert_invalid("source", "10.0.0.0/99", "source")

    def test_injection_is_rejected(self):
        self.assert_invalid("name", "regra; rm -rf /", "name")


class SequenceExecutor:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, operation, arguments=None, timeout=30):
        self.calls.append((operation, arguments, timeout))
        return self.results.pop(0)


class LinuxFirewallAdapterTests(unittest.TestCase):
    def test_create_confirmed(self):
        rule = FirewallRule(
            "DNS teste", protocol="udp", action="deny", backend="ufw",
            platform="Linux", direction="in", source="any", destination="any",
            port_start=5353, port_end=5353,
        )
        confirmed_output = (
            "Status: active\n\n"
            "[ 1] 5353/udp                  DENY IN     Anywhere                   "
            f"# DNS teste [av-id:{rule.id}]\n"
        )
        executor = SequenceExecutor([
            command_result(stdout="Rule added"),
            command_result(stdout=confirmed_output),
        ])
        adapter = LinuxAdapter(firewall_executor=executor)
        result = adapter.add_rule("add-1", rule)
        self.assertTrue(result.succeeded)
        self.assertEqual(executor.calls[0][1][3], "udp")
        self.assertIn(f"[av-id:{rule.id}]", executor.calls[0][1][-1])
        self.assertEqual(result.confirmed_state["id"], rule.id)

    def test_external_commented_rule_is_protected(self):
        rules = LinuxAdapter().parse_firewall_rules(RULE_UDP)
        self.assertEqual(len(rules), 1)
        self.assertTrue(rules[0].protected)
        self.assertFalse(rules[0].editable)

    def test_zero_exit_without_rule_is_verification_failure(self):
        executor = SequenceExecutor([
            command_result(stdout="Rule added"),
            command_result(stdout=ACTIVE_EMPTY),
        ])
        rule = FirewallRule("HTTP", 80, "tcp", "deny", backend="ufw", platform="Linux")
        result = LinuxAdapter(firewall_executor=executor).add_rule("add-2", rule)
        self.assertEqual(result.status, OperationStatus.VERIFICATION_FAILED.value)
        self.assertFalse(result.verified)

    def test_remove_confirmed(self):
        executor = SequenceExecutor([
            command_result(stdout="Rule deleted"),
            command_result(stdout=ACTIVE_EMPTY),
        ])
        rule = FirewallRule(
            "DNS teste", protocol="udp", action="deny", backend="ufw",
            platform="Linux", native_id="1", direction="in", source="any",
            destination="any", port_start=5353, port_end=5353,
        )
        result = LinuxAdapter(firewall_executor=executor).delete_rule("delete-1", rule)
        self.assertTrue(result.succeeded)
        self.assertEqual(executor.calls[0][1], ("1",))


class FirewallServiceTests(unittest.TestCase):
    def _service(self, adapter, audit=None, capability=None):
        return FirewallService(
            detector=StaticDetector(capability or linux_capability()),
            adapter=adapter,
            audit_repository=audit or MemoryAudit(),
        )

    def test_create_updates_only_from_confirmed_backend(self):
        adapter = MemoryAdapter()
        service = self._service(adapter)
        request = FirewallOperationRequest.create(
            FirewallOperation.ADD_RULE,
            payload={
                "name": "DNS", "action": "deny", "direction": "in",
                "protocol": "udp", "port": 5353, "source": "any", "destination": "any",
            },
        )
        result = service.execute(request)
        self.assertTrue(result.succeeded)
        self.assertEqual(len(service.snapshot_rules()), 1)

    def test_backend_failure_keeps_local_rule(self):
        rule = FirewallRule(
            "DNS", protocol="udp", action="deny", backend="ufw", platform="Linux",
            native_id="1", direction="in", source="any", destination="any",
            port_start=5353, port_end=5353, comment="DNS",
        )
        adapter = MemoryAdapter([rule])
        adapter.delete_result = operation_result(
            "delete", OperationStatus.EXECUTION_FAILED,
            error_code="backend_failed", verified=False,
        )
        service = self._service(adapter)
        service.execute(FirewallOperationRequest.create(FirewallOperation.LIST_RULES))
        request = FirewallOperationRequest.create(
            FirewallOperation.DELETE_RULE, rule_id=rule.id, expected_version=rule.version
        )
        result = service.execute(request)
        self.assertFalse(result.succeeded)
        self.assertEqual([item.id for item in service.snapshot_rules()], [rule.id])

    def test_two_mutations_cannot_run_simultaneously(self):
        started = threading.Event()
        release = threading.Event()
        adapter = MemoryAdapter()
        adapter.enable_gate = (started, release)
        service = self._service(adapter)
        service._capability_loaded = True
        service.capability = linux_capability()
        first = FirewallOperationRequest.create(FirewallOperation.ENABLE)
        second = FirewallOperationRequest.create(FirewallOperation.DISABLE)
        holder = {}
        thread = threading.Thread(target=lambda: holder.setdefault("first", service.execute(first)))
        thread.start()
        self.assertTrue(started.wait(1))
        result = service.execute(second)
        release.set()
        thread.join(2)
        self.assertEqual(result.status, OperationStatus.BUSY.value)
        self.assertTrue(holder["first"].succeeded)

    def test_unsupported_platform_never_reaches_adapter(self):
        capability = FirewallDetector(system_name=lambda: "Darwin").detect_capability()
        adapter = MemoryAdapter()
        service = self._service(adapter, capability=capability)
        result = service.execute(FirewallOperationRequest.create(FirewallOperation.ENABLE))
        self.assertEqual(result.status, OperationStatus.UNSUPPORTED.value)

    def test_audit_intent_failure_prevents_write(self):
        adapter = MemoryAdapter()
        service = self._service(adapter, audit=MemoryAudit(fail=True))
        result = service.execute(FirewallOperationRequest.create(FirewallOperation.ENABLE))
        self.assertEqual(result.status, OperationStatus.AUDIT_FAILED.value)

    def test_service_uses_the_same_adapter_selected_by_detector(self):
        mapping = {"ufw": "/usr/sbin/ufw", "pkexec": "/usr/bin/pkexec"}

        def runner(command, **_kwargs):
            if Path(command[0]).name == "ufw":
                return completed(stdout=ACTIVE_EMPTY)
            return completed(stdout="")

        detector = FirewallDetector(
            system_name=lambda: "Linux",
            which=lambda name: mapping.get(name),
            runner=runner,
        )
        service = FirewallService(
            detector=detector,
            audit_repository=MemoryAudit(),
        )
        result = service.execute(
            FirewallOperationRequest.create(FirewallOperation.DETECT_CAPABILITY)
        )
        self.assertTrue(result.succeeded)
        self.assertIs(service.adapter, detector.platform_adapter)


class DelayedWorker(QObject):
    operation_started = pyqtSignal(str, str)
    awaiting_authorization = pyqtSignal(str, str)
    progress = pyqtSignal(str, int)
    completed = pyqtSignal(object)
    failed = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(self, service, request, parent=None):
        super().__init__(parent)
        self.service = service
        self.request = request
        self.started = False

    def start(self):
        self.started = True

    def cancel(self):
        pass

    def isRunning(self):
        return False

    def wait(self, _timeout):
        return True

    def deleteLater(self):
        pass


class FakeViewController(QObject):
    capability_changed = pyqtSignal(object)
    rules_updated = pyqtSignal(list)
    status_changed = pyqtSignal(object)
    operation_started = pyqtSignal(str, str)
    awaiting_authorization = pyqtSignal(str, str)
    operation_progress = pyqtSignal(str, int)
    operation_completed = pyqtSignal(object)
    operation_failed = pyqtSignal(object)
    log_updated = pyqtSignal(str)

    def __init__(self, capability):
        super().__init__()
        self.capability = capability

    def refresh_capability(self):
        return "read-only"

    def refresh_status(self):
        return "read-only"

    def refresh_rules(self):
        return "read-only"

    def get_permissions(self):
        return []

    def get_wifi_networks(self):
        return []

    def get_connections(self):
        return []

    def start_monitoring(self):
        pass

    def stop_monitoring(self):
        pass

    def shutdown(self):
        return True


class ControllerWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        service = FirewallService(
            detector=StaticDetector(linux_capability()),
            adapter=MemoryAdapter(),
            audit_repository=MemoryAudit(),
        )
        service._capability_loaded = True
        service.capability = linux_capability()
        self.controller = FirewallController(service=service, worker_factory=DelayedWorker)

    def test_ui_call_returns_without_executing_slow_operation(self):
        before = time.monotonic()
        operation_id = self.controller.activate_firewall()
        elapsed = time.monotonic() - before
        self.assertLess(elapsed, 0.1)
        self.assertTrue(self.controller._workers[operation_id].started)

    def test_late_result_is_ignored(self):
        received = []
        self.controller.operation_completed.connect(received.append)
        operation_id = self.controller.refresh_status()
        worker = self.controller._workers[operation_id]
        self.controller._cleanup_worker(operation_id, None, False)
        self.controller._handle_result(
            operation_result(operation_id, confirmed_state={"active": True}),
            worker,
            True,
        )
        self.assertEqual(received, [])

    def test_view_disables_unsupported_writes(self):
        unsupported = FirewallCapability(
            platform="macOS",
            backend="macos_firewall",
            installed=False,
            active=None,
            readable=False,
            writable=False,
            requires_privilege=True,
            support_status=SupportStatus.UNSUPPORTED.value,
            reason="Escrita não suportada.",
        )
        view = FirewallView(controller=FakeViewController(unsupported))
        self.assertFalse(view.add_rule_button.isEnabled())
        self.assertFalse(view.activate_button.isEnabled())
        self.assertIn("não suportada", view.status_label.text())
        view.close()


class FirewallAuditTests(unittest.TestCase):
    def test_success_cancel_failure_and_secret_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = FirewallAuditRepository(str(Path(directory) / "audit.db"))
            request = FirewallOperationRequest.create(
                FirewallOperation.ENABLE,
                payload={"password": "never-store", "nested": {"token": "also-secret"}},
            )
            results = [
                operation_result(request.operation_id),
                operation_result(request.operation_id, OperationStatus.CANCELLED, verified=False),
                operation_result(
                    request.operation_id,
                    OperationStatus.EXECUTION_FAILED,
                    verified=False,
                    message="password=visible token:other",
                ),
            ]
            for event, result in zip(
                ("operation_completed", "privilege_cancelled", "execution_failed"), results
            ):
                repository.record(event, request, backend="ufw", result=result)
            rows = repository.list_by_operation(request.operation_id)
            serialized = " ".join(str(tuple(row)) for row in rows)
            self.assertEqual(len(rows), 3)
            self.assertNotIn("never-store", serialized)
            self.assertNotIn("also-secret", serialized)
            self.assertNotIn("visible", serialized)
            self.assertNotIn("token:other", serialized)
            repository.close()


if __name__ == "__main__":
    unittest.main()
