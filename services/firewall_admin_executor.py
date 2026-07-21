import os
import ipaddress
import re
import shutil
import subprocess
from enum import Enum

from models.firewall_contracts import (
    FirewallCommandResult,
    OperationStatus,
    PrivilegeResult,
)


class FirewallAdminOperation(str, Enum):
    UFW_STATUS = "UFW_STATUS"
    UFW_ENABLE = "UFW_ENABLE"
    UFW_DISABLE = "UFW_DISABLE"
    UFW_ADD_RULE = "UFW_ADD_RULE"
    UFW_DELETE_RULE = "UFW_DELETE_RULE"


class FirewallAdminExecutor:
    """Executa exclusivamente operações UFW previamente allowlisted."""

    WRITE_OPERATIONS = {
        FirewallAdminOperation.UFW_ENABLE.value,
        FirewallAdminOperation.UFW_DISABLE.value,
        FirewallAdminOperation.UFW_ADD_RULE.value,
        FirewallAdminOperation.UFW_DELETE_RULE.value,
    }
    SAFE_VALUE = re.compile(r"^[\w .:/()\[\]\-]{1,160}$", re.UNICODE)

    def __init__(
        self,
        runner=None,
        which=None,
        environ=None,
        executable_paths=None,
    ):
        self.runner = runner or subprocess.run
        self.which = which or shutil.which
        self.environ = environ if environ is not None else os.environ
        self.executable_paths = dict(executable_paths or {})

    def execute(self, operation, arguments=None, timeout=30):
        operation = operation.value if isinstance(operation, Enum) else str(operation)
        arguments = tuple(str(item) for item in (arguments or ()))
        if operation not in {item.value for item in FirewallAdminOperation}:
            return self._failure(
                OperationStatus.INVALID_REQUEST,
                "operation_not_allowlisted",
                "Operação administrativa não permitida.",
            )

        ufw_path = self._resolve("ufw")
        if not ufw_path:
            return self._failure(
                OperationStatus.UNAVAILABLE,
                "ufw_not_found",
                "Executável UFW não encontrado.",
                unavailable=True,
            )

        try:
            ufw_arguments = self._validated_arguments(operation, arguments)
        except ValueError as exc:
            return self._failure(
                OperationStatus.INVALID_REQUEST,
                "arguments_rejected",
                str(exc),
            )

        privileged = operation in self.WRITE_OPERATIONS
        if privileged:
            pkexec_path = self._resolve("pkexec")
            if not pkexec_path:
                return self._failure(
                    OperationStatus.UNAVAILABLE,
                    "pkexec_not_found",
                    "pkexec não está disponível para solicitar autorização.",
                    unavailable=True,
                )
            command = [pkexec_path, ufw_path, *ufw_arguments]
        else:
            command = [ufw_path, *ufw_arguments]

        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=max(1, int(timeout)),
                shell=False,
                env=self._minimal_environment(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return self._failure(
                OperationStatus.TIMED_OUT,
                "timeout",
                "A operação excedeu o tempo limite.",
                stderr=str(exc),
                timed_out=True,
            )
        except FileNotFoundError as exc:
            return self._failure(
                OperationStatus.UNAVAILABLE,
                "executable_unavailable",
                "Executável administrativo indisponível.",
                stderr=str(exc),
                unavailable=True,
            )
        except OSError as exc:
            return self._failure(
                OperationStatus.EXECUTION_FAILED,
                "os_error",
                "Falha ao iniciar a operação administrativa.",
                stderr=str(exc),
            )

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        returncode = int(completed.returncode)
        error_text = f"{stderr}\n{stdout}".lower()

        if privileged and self._agent_unavailable(error_text):
            return self._failure(
                OperationStatus.UNAVAILABLE,
                "polkit_agent_unavailable",
                "Agente de autenticação Polkit indisponível.",
                returncode,
                stdout,
                stderr,
                unavailable=True,
            )
        if privileged and (returncode == 126 or self._cancelled(error_text)):
            return self._failure(
                OperationStatus.CANCELLED,
                "authorization_cancelled",
                "Autorização cancelada pelo usuário.",
                returncode,
                stdout,
                stderr,
                cancelled=True,
            )
        if privileged and (returncode == 127 or self._denied(error_text)):
            return self._failure(
                OperationStatus.DENIED,
                "authorization_denied",
                "Autorização administrativa negada.",
                returncode,
                stdout,
                stderr,
                denied=True,
            )
        if returncode != 0:
            return self._failure(
                OperationStatus.EXECUTION_FAILED,
                "backend_exit_nonzero",
                stderr or stdout or "O UFW retornou falha.",
                returncode,
                stdout,
                stderr,
            )
        if stderr:
            return self._failure(
                OperationStatus.EXECUTION_FAILED,
                "backend_stderr",
                "O UFW retornou uma mensagem de erro.",
                returncode,
                stdout,
                stderr,
            )

        privilege = PrivilegeResult(
            status=OperationStatus.SUCCESS.value,
            granted=privileged,
            message=(
                "Autorização concedida." if privileged else "Autorização não necessária."
            ),
        )
        return FirewallCommandResult(
            status=OperationStatus.SUCCESS.value,
            exit_code=returncode,
            stdout=stdout,
            stderr=stderr,
            message="Comando executado; aguardando validação do estado.",
            privilege=privilege,
        )

    def _validated_arguments(self, operation, arguments):
        if operation == FirewallAdminOperation.UFW_STATUS.value:
            if arguments:
                raise ValueError("UFW_STATUS não aceita argumentos externos.")
            return ("status", "numbered")
        if operation == FirewallAdminOperation.UFW_ENABLE.value:
            if arguments:
                raise ValueError("UFW_ENABLE não aceita argumentos externos.")
            return ("--force", "enable")
        if operation == FirewallAdminOperation.UFW_DISABLE.value:
            if arguments:
                raise ValueError("UFW_DISABLE não aceita argumentos externos.")
            return ("disable",)
        if operation == FirewallAdminOperation.UFW_DELETE_RULE.value:
            if len(arguments) != 1 or not arguments[0].isdigit():
                raise ValueError("UFW_DELETE_RULE exige um identificador numérico.")
            return ("--force", "delete", arguments[0])
        if operation == FirewallAdminOperation.UFW_ADD_RULE.value:
            return self._validate_add_rule(arguments)
        raise ValueError("Operação não reconhecida.")

    def _validate_add_rule(self, arguments):
        if len(arguments) not in {10, 12}:
            raise ValueError("Estrutura de regra UFW inválida.")
        if arguments[0] not in {"allow", "deny"}:
            raise ValueError("Ação UFW inválida.")
        if arguments[1] not in {"in", "out"}:
            raise ValueError("Direção UFW inválida.")
        if arguments[2:10:2] != ("proto", "from", "to", "port"):
            raise ValueError("Regra UFW incompleta.")
        if arguments[3] not in {"tcp", "udp"}:
            raise ValueError("Protocolo UFW inválido.")
        self._validate_network(arguments[5])
        self._validate_network(arguments[7])
        if not re.fullmatch(r"\d{1,5}(?::\d{1,5})?", arguments[9]):
            raise ValueError("Porta UFW inválida.")
        ports = [int(value) for value in arguments[9].split(":")]
        if any(not 1 <= value <= 65535 for value in ports):
            raise ValueError("Porta UFW fora do intervalo permitido.")
        if len(ports) == 2 and ports[0] > ports[1]:
            raise ValueError("Faixa de portas UFW inválida.")
        if len(arguments) == 12 and arguments[10] != "comment":
            raise ValueError("Comentário UFW inválido.")
        for value in arguments:
            if not self.SAFE_VALUE.fullmatch(value):
                raise ValueError("Argumento UFW rejeitado pela allowlist.")
        return arguments

    @staticmethod
    def _validate_network(value):
        if value == "any":
            return
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise ValueError("Endereço de rede UFW inválido.") from exc

    def _resolve(self, executable):
        configured = self.executable_paths.get(executable)
        path = configured or self.which(executable)
        if not path:
            return None
        path = os.path.realpath(str(path))
        return path if os.path.isabs(path) else None

    def _minimal_environment(self):
        allowed = (
            "DISPLAY",
            "XAUTHORITY",
            "WAYLAND_DISPLAY",
            "XDG_RUNTIME_DIR",
            "DBUS_SESSION_BUS_ADDRESS",
        )
        environment = {
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG": "C",
            "LC_ALL": "C",
        }
        for key in allowed:
            value = self.environ.get(key)
            if value:
                environment[key] = value
        return environment

    @staticmethod
    def _agent_unavailable(text):
        return "no authentication agent" in text or "authentication agent not found" in text

    @staticmethod
    def _cancelled(text):
        return "dismissed" in text or "cancelled" in text or "canceled" in text

    @staticmethod
    def _denied(text):
        return "not authorized" in text or "permission denied" in text

    @staticmethod
    def _failure(
        status,
        error_code,
        message,
        exit_code=None,
        stdout="",
        stderr="",
        *,
        cancelled=False,
        denied=False,
        unavailable=False,
        timed_out=False,
    ):
        status_value = status.value if isinstance(status, Enum) else str(status)
        privilege = PrivilegeResult(
            status=status_value,
            cancelled=cancelled,
            denied=denied,
            unavailable=unavailable,
            timed_out=timed_out,
            message=message,
            technical_details=stderr,
        )
        return FirewallCommandResult(
            status=status_value,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            error_code=error_code,
            message=message,
            privilege=privilege,
        )
