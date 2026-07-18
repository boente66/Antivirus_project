import os
import platform
from pathlib import Path

from services.threat_score_service import ThreatScoreService


class ThreatActionService:

    ACTION_QUARANTINE = "quarantine"
    ACTION_SUGGEST_QUARANTINE = "suggest_quarantine"
    ACTION_ALERT = "alert"
    ACTION_IGNORE = "ignore"

    SCORE_ALERT = 1
    SCORE_SUGGEST_QUARANTINE = 20
    SCORE_AUTO_QUARANTINE = 70

    # --------------------------------------------------
    # Diretórios críticos por sistema operacional
    # --------------------------------------------------

    LINUX_SYSTEM_PATHS = (
        "/usr",
        "/bin",
        "/sbin",
        "/etc",
        "/lib",
        "/lib64",
        "/boot",
        "/dev",
        "/proc",
        "/sys"
    )

    WINDOWS_SYSTEM_PATHS = (
        "c:\\windows",
        "c:\\program files",
        "c:\\program files (x86)"
    )

    MAC_SYSTEM_PATHS = (
        "/system",
        "/usr",
        "/bin",
        "/sbin",
        "/etc",
        "/var",
        "/applications"
    )

    # --------------------------------------------------

    def __init__(self, auto_quarantine_enabled=True):

        self.scorer = ThreatScoreService()
        self.auto_quarantine_enabled = bool(auto_quarantine_enabled)

        system = platform.system()

        if system == "Windows":
            self.system_paths = self.WINDOWS_SYSTEM_PATHS

        elif system == "Darwin":
            self.system_paths = self.MAC_SYSTEM_PATHS

        else:
            self.system_paths = self.LINUX_SYSTEM_PATHS

    # ======================================================
    # DECISÃO PRINCIPAL
    # ======================================================

    def decide(self, file_path: str, virus_name: str) -> str:

        if not file_path:
            return self.ACTION_IGNORE

        try:
            path = Path(file_path).resolve()
        except Exception:
            return self.ACTION_IGNORE

        # --------------------------------
        # arquivos do sistema nunca devem
        # ser removidos automaticamente
        # --------------------------------

        if self._is_system_path(path):
            return self.ACTION_IGNORE

        # --------------------------------
        # cálculo de score
        # --------------------------------

        score = self.scorer.calculate(
            file_path=path,
            virus_name=virus_name
        )

        # --------------------------------
        # decisão baseada em score
        # --------------------------------

        if score >= self.SCORE_AUTO_QUARANTINE:
            if self.auto_quarantine_enabled:
                return self.ACTION_QUARANTINE

            return self.ACTION_SUGGEST_QUARANTINE

        if score >= self.SCORE_SUGGEST_QUARANTINE:
            return self.ACTION_SUGGEST_QUARANTINE

        if virus_name or score >= self.SCORE_ALERT:
            return self.ACTION_ALERT

        return self.ACTION_IGNORE

    # ======================================================
    # REGRAS
    # ======================================================

    def _is_system_path(self, path: Path) -> bool:

        for p in self.system_paths:
            try:
                critical = Path(p).resolve()

                if path == critical:
                    return True

                if critical.anchor == str(critical):
                    continue

                path.relative_to(critical)

                return True

            except ValueError:
                continue

            except Exception:
                path_text = str(path).lower()
                critical_text = str(p).lower().rstrip(os.sep)

                if path_text == critical_text:
                    return True

        return False
