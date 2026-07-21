import os
import logging
import re
import shutil
import subprocess
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import psutil

from .platform_adapter import PlatformAdapter
from models.firewall_contracts import (
    FirewallCapability,
    FirewallOperationResult,
    OperationStatus,
    SupportStatus,
)
from models.firewall_rule import FirewallRule
from services.firewall_admin_executor import (
    FirewallAdminExecutor,
    FirewallAdminOperation,
)


class LinuxAdapter(PlatformAdapter):

    _logger = logging.getLogger(__name__)
    backend = "ufw"
    platform = "Linux"
    RULE_PATTERN = re.compile(
        r"^\[\s*(?P<number>\d+)\]\s+"
        r"(?P<target>.+?)\s{2,}"
        r"(?P<action>ALLOW|DENY|REJECT|LIMIT)\s+"
        r"(?P<direction>IN|OUT)\s+"
        r"(?P<source>.+?)\s*$"
    )
    PORT_PATTERN = re.compile(
        r"^(?P<start>\d+)(?::(?P<end>\d+))?/(?P<protocol>tcp|udp)(?:\s+\(v6\))?$",
        re.IGNORECASE,
    )
    INTERNAL_ID_PATTERN = re.compile(
        r"\s*\[av-id:(?P<id>[0-9a-fA-F-]{36})\]\s*$"
    )

    def __init__(self, firewall_executor=None):
        self._firewall_executor = firewall_executor

    # --------------------------------------------------
    # Sistema operacional
    # --------------------------------------------------

    def get_os_name(self):
        return "Linux"

    # --------------------------------------------------
    # Diretório do usuário
    # --------------------------------------------------

    def get_home_directory(self):
        return os.path.expanduser("~")

    # --------------------------------------------------
    # Volumes do sistema
    # --------------------------------------------------

    def get_volumes(self):

        volumes = []

        try:

            result = subprocess.run(
                ["df", "-P"],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.splitlines()[1:]

            for line in lines:

                parts = line.split()

                if len(parts) >= 6:

                    volumes.append({
                        "device": parts[0],
                        "mountpoint": parts[5],
                        "filesystem": parts[1]
                    })

        except Exception:
            pass

        return volumes

    # --------------------------------------------------
    # Programas instalados
    # --------------------------------------------------

    def get_installed_programs(self):

        programs = []

        try:

            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"],
                capture_output=True,
                text=True,
                timeout=15
            )

            for line in result.stdout.splitlines():

                parts = line.split("\t")

                if len(parts) >= 2:

                    programs.append({
                        "name": parts[0],
                        "version": parts[1]
                    })

        except Exception:

            try:

                result = subprocess.run(
                    ["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}\n"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                for line in result.stdout.splitlines():

                    parts = line.split("\t")

                    if len(parts) >= 2:

                        programs.append({
                            "name": parts[0],
                            "version": parts[1]
                        })

            except Exception:
                pass

        return programs

    # --------------------------------------------------
    # Diretórios inteligentes para scan
    # --------------------------------------------------

    def get_smart_scan_targets(self):

        home = Path.home()

        targets = [

            home / "Downloads",
            home / "Desktop",
            home / "Documents",
            home / "Pictures",
            home / "Videos",

            home / ".config" / "autostart",
            home / ".local" / "bin",
            home / ".local" / "share" / "applications",

            Path("/tmp"),
            Path("/var/tmp"),

            Path("/usr/bin"),
            Path("/usr/local/bin")
        ]

        return [p for p in targets if p.exists()]

    # --------------------------------------------------
    # Scan WiFi networks
    # --------------------------------------------------

    def scan_wifi_networks(self):

        networks = []

        try:

            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            seen = set()

            for line in result.stdout.splitlines():

                parts = line.split(":")

                if len(parts) < 3:
                    continue

                ssid = parts[0].strip()

                if not ssid or ssid in seen:
                    continue

                seen.add(ssid)

                networks.append({
                    "ssid": ssid,
                    "signal": parts[1],
                    "security": parts[2]
                })

        except Exception:
            pass

        return networks

    # --------------------------------------------------
    # Processos em execução
    # --------------------------------------------------

    def get_running_processes(self):
        processes = []
        try:
            for process in psutil.process_iter(attrs=["pid", "name"]):
                try:
                    info = process.info
                    name = str(info.get("name") or "").strip()
                    pid = int(info.get("pid"))
                    if not name:
                        continue
                    processes.append({
                        "pid": pid,
                        "name": name,
                    })
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess) as exc:
                    self._logger.debug("Processo indisponível durante enumeração: %s", exc)
                except (AttributeError, TypeError, ValueError) as exc:
                    self._logger.debug("Dados de processo inválidos: %s", exc)
        except (psutil.AccessDenied, psutil.NoSuchProcess) as exc:
            self._logger.warning("Enumeração de processos indisponível: %s", exc)
        except Exception as exc:
            self._logger.warning("Falha inesperada ao enumerar processos: %s", exc)
        return processes

    # --------------------------------------------------
    # Firewall status
    # --------------------------------------------------

    def get_firewall_status(self):
        result = self.read_status("platform-status")
        if not result.succeeded or not isinstance(result.confirmed_state, dict):
            return "unknown"
        active = result.confirmed_state.get("active")
        return "active" if active is True else "inactive" if active is False else "unknown"

    def create_firewall_adapter(self, executor=None):
        if executor is not None:
            self._firewall_executor = executor
        return self

    def detect_firewall_capability(
        self,
        *,
        which=None,
        runner=None,
        executor=None,
    ):
        """Detecta UFW e conflitos respeitando particularidades do Linux."""
        which = which or shutil.which
        runner = runner or subprocess.run
        ufw_path = which("ufw")
        other_active = self._active_non_ufw_backends(which, runner)
        if not ufw_path:
            backend = other_active[0] if len(other_active) == 1 else "unknown"
            status = (
                SupportStatus.BACKEND_CONFLICT.value
                if len(other_active) > 1
                else SupportStatus.UNSUPPORTED.value
            )
            reason = (
                f"Backend(s) ativo(s) sem suporte de escrita: {', '.join(other_active)}."
                if other_active else "UFW não está instalado."
            )
            return FirewallCapability(
                platform=self.platform,
                backend=backend,
                installed=bool(other_active),
                active=True if other_active else None,
                readable=bool(other_active),
                writable=False,
                requires_privilege=True,
                support_status=status,
                reason=reason,
            )

        self.create_firewall_adapter(executor)
        status_result = self.read_status("capability-probe")
        if other_active:
            return FirewallCapability(
                platform=self.platform,
                backend=self.backend,
                installed=True,
                active=(
                    status_result.confirmed_state.get("active")
                    if status_result.succeeded else None
                ),
                readable=status_result.succeeded,
                writable=False,
                requires_privilege=True,
                support_status=SupportStatus.BACKEND_CONFLICT.value,
                reason=(
                    "UFW está presente, mas outro backend parece ativo: "
                    f"{', '.join(other_active)}."
                ),
            )
        if not status_result.succeeded:
            return FirewallCapability(
                platform=self.platform,
                backend=self.backend,
                installed=True,
                active=None,
                readable=False,
                writable=False,
                requires_privilege=True,
                support_status=SupportStatus.UNAVAILABLE.value,
                reason=(
                    status_result.message
                    or "UFW instalado, mas seu estado não pôde ser consultado."
                ),
            )

        pkexec_available = bool(which("pkexec"))
        active = bool(status_result.confirmed_state.get("active"))
        return FirewallCapability(
            platform=self.platform,
            backend=self.backend,
            installed=True,
            active=active,
            readable=True,
            writable=pkexec_available,
            requires_privilege=True,
            support_status=(
                SupportStatus.SUPPORTED.value
                if pkexec_available else SupportStatus.READ_ONLY.value
            ),
            reason=(
                "UFW disponível e validado."
                if pkexec_available else "UFW legível, mas pkexec não está disponível."
            ),
        )

    def _active_non_ufw_backends(self, which, runner):
        active = []
        firewall_cmd = which("firewall-cmd")
        if firewall_cmd:
            result = self._probe_firewall_command(
                [firewall_cmd, "--state"], runner
            )
            if (
                result
                and result.returncode == 0
                and "running" in (result.stdout or "").lower()
            ):
                active.append("firewalld")

        nft = which("nft")
        if nft:
            result = self._probe_firewall_command(
                [nft, "list", "ruleset"], runner
            )
            output = (
                (result.stdout or "")
                if result and result.returncode == 0 else ""
            )
            if output.strip() and "ufw" not in output.lower():
                active.append("nftables")
        return active

    @staticmethod
    def _probe_firewall_command(command, runner):
        try:
            return runner(
                [
                    os.path.realpath(str(part)) if index == 0 else str(part)
                    for index, part in enumerate(command)
                ],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
                env={
                    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                    "LANG": "C",
                    "LC_ALL": "C",
                },
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    @property
    def firewall_executor(self):
        if self._firewall_executor is None:
            self._firewall_executor = FirewallAdminExecutor()
        return self._firewall_executor

    def read_status(self, operation_id="status"):
        command = self.firewall_executor.execute(FirewallAdminOperation.UFW_STATUS)
        if not command.succeeded:
            return self._firewall_result_from_command(operation_id, command)
        active = self._parse_firewall_active(command.stdout)
        if active is None:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.VERIFICATION_FAILED.value,
                backend=self.backend,
                verified=False,
                exit_code=command.exit_code,
                stdout=command.stdout,
                stderr=command.stderr,
                error_code="status_unrecognized",
                message="Não foi possível interpretar o estado retornado pelo UFW.",
            )
        return FirewallOperationResult(
            operation_id=operation_id,
            status=OperationStatus.SUCCESS.value,
            backend=self.backend,
            confirmed_state={"active": active},
            verified=True,
            exit_code=command.exit_code,
            stdout=command.stdout,
            message="Estado do UFW confirmado.",
        )

    def list_rules(self, operation_id="list_rules"):
        command = self.firewall_executor.execute(FirewallAdminOperation.UFW_STATUS)
        if not command.succeeded:
            return self._firewall_result_from_command(operation_id, command), []
        active = self._parse_firewall_active(command.stdout)
        if active is None:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.VERIFICATION_FAILED.value,
                backend=self.backend,
                verified=False,
                stdout=command.stdout,
                error_code="status_unrecognized",
                message="Listagem do UFW não pôde ser validada.",
            ), []
        rules = self.parse_firewall_rules(command.stdout)
        return FirewallOperationResult(
            operation_id=operation_id,
            status=OperationStatus.SUCCESS.value,
            backend=self.backend,
            confirmed_state={"active": active, "rule_count": len(rules)},
            verified=True,
            exit_code=command.exit_code,
            stdout=command.stdout,
            message="Regras do UFW confirmadas.",
        ), rules

    def enable(self, operation_id):
        return self._change_firewall_state(
            operation_id, FirewallAdminOperation.UFW_ENABLE, True
        )

    def disable(self, operation_id):
        return self._change_firewall_state(
            operation_id, FirewallAdminOperation.UFW_DISABLE, False
        )

    def _change_firewall_state(self, operation_id, operation, requested_active):
        before = self.read_status(f"{operation_id}:before")
        command = self.firewall_executor.execute(operation)
        requested = {"active": requested_active}
        if not command.succeeded:
            return self._firewall_result_from_command(operation_id, command, requested)
        confirmation = self.read_status(f"{operation_id}:verify")
        verified = (
            confirmation.succeeded
            and confirmation.confirmed_state.get("active") is requested_active
        )
        return self._firewall_mutation_result(
            operation_id,
            command,
            requested,
            confirmation,
            verified,
            changed=before.confirmed_state != requested if before.succeeded else True,
        )

    def add_rule(self, operation_id, rule):
        arguments = self.build_firewall_add_arguments(rule)
        command = self.firewall_executor.execute(
            FirewallAdminOperation.UFW_ADD_RULE, arguments
        )
        if not command.succeeded:
            return self._firewall_result_from_command(
                operation_id, command, rule.to_dict()
            )
        verification, rules = self.list_rules(f"{operation_id}:verify")
        confirmed = next(
            (item for item in rules if self.rules_match(item, rule)), None
        )
        verified = verification.succeeded and confirmed is not None
        return self._firewall_mutation_result(
            operation_id,
            command,
            rule.to_dict(),
            verification,
            verified,
            changed=verified,
            confirmed_state=confirmed.to_dict() if confirmed else None,
        )

    def delete_rule(self, operation_id, rule):
        if not rule.native_id or not str(rule.native_id).isdigit():
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.INVALID_REQUEST.value,
                backend=self.backend,
                requested_state=rule.to_dict(),
                verified=False,
                error_code="native_id_required",
                message="A regra não possui identificador UFW seguro para remoção.",
            )
        command = self.firewall_executor.execute(
            FirewallAdminOperation.UFW_DELETE_RULE, (str(rule.native_id),)
        )
        if not command.succeeded:
            return self._firewall_result_from_command(
                operation_id, command, rule.to_dict()
            )
        verification, rules = self.list_rules(f"{operation_id}:verify")
        still_exists = any(self.rules_match(item, rule) for item in rules)
        verified = verification.succeeded and not still_exists
        return self._firewall_mutation_result(
            operation_id,
            command,
            rule.to_dict(),
            verification,
            verified,
            changed=verified,
            confirmed_state={"absent": not still_exists} if verification.succeeded else None,
        )

    def build_firewall_add_arguments(self, rule):
        port = (
            str(rule.port_start)
            if rule.port_start == rule.port_end
            else f"{rule.port_start}:{rule.port_end}"
        )
        arguments = [
            rule.action,
            rule.direction,
            "proto",
            rule.protocol,
            "from",
            rule.source,
            "to",
            rule.destination,
            "port",
            port,
        ]
        comment = rule.comment or rule.name
        arguments.extend(("comment", f"{comment} [av-id:{rule.id}]".strip()))
        return tuple(arguments)

    def parse_firewall_rules(self, output):
        rules = []
        for raw_line in str(output or "").splitlines():
            match = self.RULE_PATTERN.match(raw_line.strip())
            if not match:
                continue
            target = match.group("target").strip()
            comment = ""
            if " # " in match.group("source"):
                source, comment = match.group("source").split(" # ", 1)
            else:
                source = match.group("source")
            source = source.replace("(v6)", "").strip()
            port_match = self.PORT_PATTERN.match(target)
            if not port_match:
                continue
            start = int(port_match.group("start"))
            end = int(port_match.group("end") or start)
            action = match.group("action").lower()
            action = "deny" if action in {"deny", "reject"} else "allow"
            raw_comment = comment.strip()
            internal_match = self.INTERNAL_ID_PATTERN.search(raw_comment)
            internal_id = internal_match.group("id") if internal_match else None
            clean_comment = (
                self.INTERNAL_ID_PATTERN.sub("", raw_comment).strip()
                if internal_match else raw_comment
            )
            native_id = match.group("number")
            external_id = uuid5(
                NAMESPACE_URL,
                f"ufw-external:{native_id}:{target}:{action}:{source}",
            )
            rules.append(FirewallRule(
                name=clean_comment or f"UFW {native_id}",
                id=internal_id or external_id,
                native_id=native_id,
                backend=self.backend,
                platform=self.platform,
                action=action,
                direction=match.group("direction").lower(),
                protocol=port_match.group("protocol").lower(),
                source="any" if source.lower().startswith("anywhere") else source,
                destination="any",
                port_start=start,
                port_end=end,
                comment=clean_comment,
                origin="user" if internal_id else "system",
                protected=not bool(internal_id),
                editable=bool(internal_id),
            ))
        return rules

    @staticmethod
    def rules_match(current, requested):
        return all((
            current.action == requested.action,
            current.direction == requested.direction,
            current.protocol == requested.protocol,
            current.source == requested.source,
            current.destination == requested.destination,
            current.port_start == requested.port_start,
            current.port_end == requested.port_end,
        ))

    @staticmethod
    def _parse_firewall_active(output):
        text = str(output or "").lower()
        if re.search(r"^status:\s+active\s*$", text, re.MULTILINE):
            return True
        if re.search(r"^status:\s+inactive\s*$", text, re.MULTILINE):
            return False
        return None

    def _firewall_mutation_result(
        self,
        operation_id,
        command,
        requested_state,
        confirmation,
        verified,
        changed,
        confirmed_state=None,
    ):
        if not verified:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.VERIFICATION_FAILED.value,
                backend=self.backend,
                requested_state=requested_state,
                confirmed_state=confirmed_state or confirmation.confirmed_state,
                changed=False,
                verified=False,
                exit_code=command.exit_code,
                stdout=command.stdout,
                stderr=confirmation.stderr,
                error_code="post_verification_failed",
                message="O comando foi executado, mas a alteração não foi confirmada.",
            )
        return FirewallOperationResult(
            operation_id=operation_id,
            status=OperationStatus.SUCCESS.value,
            backend=self.backend,
            requested_state=requested_state,
            confirmed_state=confirmed_state or confirmation.confirmed_state,
            changed=changed,
            verified=True,
            exit_code=command.exit_code,
            stdout=command.stdout,
            message="Alteração confirmada no UFW.",
        )

    def _firewall_result_from_command(
        self, operation_id, command, requested_state=None
    ):
        return FirewallOperationResult(
            operation_id=operation_id,
            status=command.status,
            backend=self.backend,
            requested_state=requested_state,
            changed=False,
            verified=False,
            exit_code=command.exit_code,
            stdout=command.stdout,
            stderr=command.stderr,
            error_code=command.error_code,
            message=command.message,
        )

    # --------------------------------------------------
    # Usuários do sistema
    # --------------------------------------------------

    def get_system_users(self):

        users = []

        try:

            with open("/etc/passwd") as f:

                for line in f:

                    parts = line.split(":")

                    if len(parts) >= 3:

                        uid = int(parts[2])

                        if uid >= 1000:
                            users.append(parts[0])

        except Exception:
            pass

        return users

    # --------------------------------------------------
    # Diretórios temporários
    # --------------------------------------------------

    def get_temp_directories(self):

        return [
            "/tmp",
            "/var/tmp"
        ]

    # --------------------------------------------------
    # Diretórios críticos do sistema
    # --------------------------------------------------

    def get_system_directories(self):

        return [
            "/",
            "/usr",
            "/bin",
            "/boot",
            "/etc",
            "/lib",
            "/lib64",
            "/dev",
            "/root",
            "/run",
            "/sbin",
            "/sys",
            "/proc",
            "/var"
        ]

    # --------------------------------------------------
    # Verificar privilégios admin
    # --------------------------------------------------

    def has_admin_privileges(self):

        try:
            return os.geteuid() == 0
        except Exception:
            return False

    def get_cleaner_capabilities(self):
        return {
            "supported": True,
            "message": "Limpeza segura disponível no Linux.",
        }
