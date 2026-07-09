import os
import platform
from pathlib import Path


class ThreatScoreService:

    # --------------------------------------------------
    # SCORES BASEADOS EM ASSINATURA
    # --------------------------------------------------

    SCORE_RANSOMWARE = 100
    SCORE_TROJAN = 90
    SCORE_WORM = 80
    SCORE_BACKDOOR = 70
    SCORE_SPYWARE = 60

    # --------------------------------------------------
    # SCORES HEURÍSTICOS
    # --------------------------------------------------

    SCORE_SCRIPT = 30
    SCORE_EXECUTABLE = 40
    SCORE_TEMP_LOCATION = 20
    SCORE_DOWNLOAD_LOCATION = 10

    # --------------------------------------------------
    # EXTENSÕES SUSPEITAS
    # --------------------------------------------------

    SCRIPT_EXTENSIONS = (
        ".sh",
        ".py",
        ".js",
        ".php",
        ".pl",
        ".rb",
        ".ps1",
        ".bat"
    )

    EXEC_EXTENSIONS = (
        ".exe",
        ".bin",
        ".run",
        ".appimage",
        ".dll",
        ".scr",
        ".com"
    )

    # --------------------------------------------------
    # PATHS SUSPEITOS
    # --------------------------------------------------

    LINUX_TEMP_PATHS = (
        "/tmp",
        "/var/tmp"
    )

    WINDOWS_TEMP_PATHS = (
        "c:\\windows\\temp",
        "c:\\temp"
    )

    MAC_TEMP_PATHS = (
        "/tmp",
        "/var/tmp"
    )

    # --------------------------------------------------

    def __init__(self):

        system = platform.system()

        if system == "Windows":
            self.temp_paths = self.WINDOWS_TEMP_PATHS

        elif system == "Darwin":
            self.temp_paths = self.MAC_TEMP_PATHS

        else:
            self.temp_paths = self.LINUX_TEMP_PATHS

    # --------------------------------------------------
    # CALCULO PRINCIPAL
    # --------------------------------------------------

    def calculate(self, file_path: str, virus_name: str):

        score = 0

        virus = (virus_name or "").lower()

        try:
            path = str(Path(file_path).resolve()).lower()
        except Exception:
            path = (file_path or "").lower()

        # --------------------------------
        # assinatura de vírus
        # --------------------------------

        if "ransom" in virus:
            score += self.SCORE_RANSOMWARE

        if "trojan" in virus:
            score += self.SCORE_TROJAN

        if "worm" in virus:
            score += self.SCORE_WORM

        if "backdoor" in virus:
            score += self.SCORE_BACKDOOR

        if "spy" in virus:
            score += self.SCORE_SPYWARE

        # --------------------------------
        # extensão suspeita
        # --------------------------------

        if path.endswith(self.SCRIPT_EXTENSIONS):
            score += self.SCORE_SCRIPT

        if path.endswith(self.EXEC_EXTENSIONS):
            score += self.SCORE_EXECUTABLE

        # --------------------------------
        # local suspeito
        # --------------------------------

        for temp in self.temp_paths:

            if path.startswith(temp):
                score += self.SCORE_TEMP_LOCATION
                break

        if "downloads" in path:
            score += self.SCORE_DOWNLOAD_LOCATION

        # --------------------------------
        # limite de score
        # --------------------------------

        if score > 100:
            score = 100

        return score