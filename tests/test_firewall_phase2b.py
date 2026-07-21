import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from core.platform.linux_adapter import LinuxAdapter
from models.firewall_contracts import (
    FirewallApplicationProfile,
    FirewallCommandResult,
    FirewallOperation,
    FirewallOperationRequest,
    FirewallOperationResult,
    OperationStatus,
)
from models.firewall_rule import FirewallRule
from services.firewall_admin_executor import (
    FirewallAdminExecutor,
    FirewallAdminOperation,
)
from services.firewall_service import FirewallService
from views.wifi_view import WiFiView


ACTIVE_EMPTY = "Status: active\n\nTo  Action  From\n"
PROFILE_RULE = (
    "Status: active\n\n"
    "[ 1] OpenSSH                    DENY IN     Anywhere"
    "                   # Aplicação OpenSSH "
    "[av-id:12345678-1234-1234-1234-123456789abc]\n"
)


def completed(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def operation_result(operation_id, confirmed_state=None):
    return FirewallOperationResult(
        operation_id=operation_id,
        status=OperationStatus.SUCCESS.value,
        backend="ufw",
        confirmed_state=confirmed_state,
        verified=True,
        message="ok",
    )


class SequenceExecutor:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, operation, arguments=None, timeout=30):
        self.calls.append((operation, tuple(arguments or ())))
        return self.results.pop(0)


def command_result(stdout=""):
    return FirewallCommandResult(
        status=OperationStatus.SUCCESS.value,
        exit_code=0,
        stdout=stdout,
        message="ok",
    )


class AuthorizedReadTests(unittest.TestCase):
    PATHS = {"ufw": "/usr/sbin/ufw", "pkexec": "/usr/bin/pkexec"}

    def test_status_uses_pkexec_without_shell(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return completed(stdout=ACTIVE_EMPTY)

        result = FirewallAdminExecutor(
            runner=runner, which=lambda name: self.PATHS.get(name)
        ).execute(FirewallAdminOperation.UFW_STATUS)

        self.assertTrue(result.succeeded)
        self.assertEqual(
            calls[0][0],
            ["/usr/bin/pkexec", "/usr/sbin/ufw", "status", "numbered"],
        )
        self.assertFalse(calls[0][1]["shell"])

    def test_application_list_uses_allowlisted_command(self):
        calls = []

        def runner(command, **_kwargs):
            calls.append(command)
            return completed(stdout="Available applications:\n  OpenSSH\n")

        result = FirewallAdminExecutor(
            runner=runner, which=lambda name: self.PATHS.get(name)
        ).execute(FirewallAdminOperation.UFW_APP_LIST)

        self.assertTrue(result.succeeded)
        self.assertEqual(calls[0][-2:], ["app", "list"])

    def test_application_profile_injection_is_rejected(self):
        executor = FirewallAdminExecutor(which=lambda name: self.PATHS.get(name))
        result = executor.execute(
            FirewallAdminOperation.UFW_ADD_APPLICATION_RULE,
            ("deny", "in", "OpenSSH; reboot", "comment", "teste"),
        )
        self.assertEqual(result.status, OperationStatus.INVALID_REQUEST.value)


class ApplicationProfileAdapterTests(unittest.TestCase):
    def test_profiles_are_structured_and_deduplicated(self):
        profiles = LinuxAdapter.parse_application_profiles(
            "Available applications:\n  OpenSSH\n  CUPS\n  OpenSSH\n"
        )
        self.assertEqual([item.name for item in profiles], ["OpenSSH", "CUPS"])
        self.assertTrue(all(isinstance(item, FirewallApplicationProfile) for item in profiles))

    def test_managed_application_rule_is_parsed_and_removable(self):
        rule = LinuxAdapter().parse_firewall_rules(PROFILE_RULE)[0]
        self.assertEqual(rule.application, "OpenSSH")
        self.assertEqual(rule.action, "deny")
        self.assertTrue(rule.editable)
        self.assertFalse(rule.protected)
        self.assertEqual(rule.native_id, "1")

    def test_application_rule_builds_allowlisted_arguments(self):
        rule = FirewallRule(
            name="Aplicação OpenSSH",
            protocol="any",
            action="deny",
            direction="in",
            application="OpenSSH",
        )
        arguments = LinuxAdapter.build_application_rule_arguments(rule)
        self.assertEqual(arguments[:3], ("deny", "in", "OpenSSH"))
        self.assertEqual(arguments[3], "comment")
        self.assertIn("[av-id:", arguments[4])

    def test_adapter_verifies_application_rule_after_add(self):
        new_rule = FirewallRule(
            name="Aplicação OpenSSH",
            protocol="any",
            action="deny",
            direction="in",
            application="OpenSSH",
            id="12345678-1234-1234-1234-123456789abc",
        )
        executor = SequenceExecutor([
            command_result("Rule added"),
            command_result(PROFILE_RULE),
        ])
        result = LinuxAdapter(firewall_executor=executor).add_rule("op", new_rule)
        self.assertTrue(result.succeeded)
        self.assertEqual(
            executor.calls[0][0],
            FirewallAdminOperation.UFW_ADD_APPLICATION_RULE,
        )


class ApplicationServiceTests(unittest.TestCase):
    def test_service_merges_profiles_with_confirmed_rules(self):
        managed_rule = LinuxAdapter().parse_firewall_rules(PROFILE_RULE)[0]

        class Adapter:
            def list_rules(self, operation_id):
                return operation_result(operation_id), [managed_rule]

            def list_firewall_applications(self, operation_id):
                return operation_result(operation_id), [
                    FirewallApplicationProfile("OpenSSH"),
                    FirewallApplicationProfile("CUPS"),
                ]

        service = FirewallService(
            adapter=Adapter(),
            audit_repository=SimpleNamespace(record=lambda *_args, **_kwargs: 1),
        )
        service._capability_loaded = True
        service.capability = SimpleNamespace(
            readable=True,
            writable=True,
            write_blocked=False,
            backend="ufw",
        )
        result = service.execute(
            FirewallOperationRequest.create(FirewallOperation.LIST_APPLICATIONS)
        )
        self.assertTrue(result.succeeded)
        profiles = {item.name: item for item in result.confirmed_state}
        self.assertEqual(profiles["OpenSSH"].action, "deny")
        self.assertTrue(profiles["OpenSSH"].managed)
        self.assertIsNone(profiles["CUPS"].action)


class WiFiRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_structured_networks_are_rendered_as_text(self):
        class Controller:
            def scan_wifi_networks(self):
                return [{"ssid": "Rede Teste", "signal": "85", "security": "WPA2"}]

            def get_wifi_networks(self):
                return []

        view = WiFiView(Controller())
        view.scan_wifi()
        self.assertEqual(view.wifi_list.count(), 1)
        self.assertIn("Rede Teste", view.wifi_list.item(0).text())
        self.assertIn("WPA2", view.wifi_list.item(0).text())


class DiagnosticTests(unittest.TestCase):
    def test_missing_pkexec_is_reported_without_mutation(self):
        paths = {"ufw": "/usr/sbin/ufw", "systemctl": "/usr/bin/systemctl"}
        with patch(
            "core.platform.linux_adapter.shutil.which",
            side_effect=lambda name: paths.get(name),
        ), patch.object(
            LinuxAdapter,
            "_read_ufw_service_state",
            return_value={"ufw_service_enabled": True, "ufw_service_active": True},
        ):
            result = LinuxAdapter().diagnose_firewall("diag")
        self.assertFalse(result.succeeded)
        self.assertIn("pkexec", " ".join(result.confirmed_state["problems"]))


if __name__ == "__main__":
    unittest.main()
