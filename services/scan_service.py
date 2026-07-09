# services/scan_service.py

import os
from pathlib import Path
from datetime import datetime

from core.platform.platform_factory import PlatformFactory
from database.repositories.scan_history_repository import ScanHistoryRepository

from models.detected_file import DetectedFile
from models.virus_model import Virus

from services.clamav_service import ClamAVService
from services.detection_pipeline import DetectionPipeline
from services.file_identification_service import FileIdentificationService
from services.threat_score_service import ThreatScoreService




class ScanService:
    """
    Serviço responsável por:

    - fornecer alvos de escaneamento
    - iterar arquivos
    - registrar histórico
    - comunicar com o engine (ClamAVService)
    - executar análise de detecção
    - adaptar comportamento ao sistema operacional
    """

    def __init__(self):

        self.history_repo = ScanHistoryRepository()

        # Adapter do sistema operacional
        self.platform = PlatformFactory.get_adapter()

        # Engine antivírus
        self.clamav = ClamAVService()

        # Serviços auxiliares
        self.identifier = FileIdentificationService()
        self.scorer = ThreatScoreService()

        # Pipeline de detecção
        self.pipeline = DetectionPipeline(
            self.clamav,
            self.identifier,
            self.scorer
        )

    # ==================================================
    # ENGINE
    # ==================================================

    def connect_engine(self):
        """
        Tenta conectar automaticamente ao ClamAV.
        """
        return self.clamav.auto_connect()

    # --------------------------------------------------

    def is_connected(self):
        """
        Verifica se o engine está conectado.
        """
        return self.clamav.is_connected()

    # --------------------------------------------------

    def engine_status(self):
        """
        Retorna status do daemon ClamAV.
        """
        return self.clamav.get_status()

    # --------------------------------------------------

    def scan_file(self, file_path):
        """
        Realiza scan direto no engine.
        """
        return self.clamav.scan_file(file_path)

    # --------------------------------------------------

    def analyze_file(self, file_path):
        """
        Executa pipeline completo de detecção.
        """
        return self.pipeline.analyze(file_path)

    # ==================================================
    # SMART SCAN TARGETS
    # ==================================================

    def get_smart_scan_targets(self):
        """
        Retorna diretórios inteligentes de scan
        conforme o sistema operacional.
        """

        try:
            return self.platform.get_smart_scan_targets()
        except Exception:
            return []

    # ==================================================
    # ITERAÇÃO DE ARQUIVOS
    # ==================================================

    def iter_files(self, base_path):

        base_path = Path(base_path)

        if not base_path.exists():
            return

        for root, dirs, files in os.walk(base_path):

            # ignorar diretórios de cache
            dirs[:] = [
                d for d in dirs
                if d not in (
                    "cache",
                    ".cache",
                    "Trash",
                    "thumbnails"
                )
            ]

            for file in files:

                yield os.path.join(root, file)

    # ==================================================
    # HISTÓRICO DE SCAN
    # ==================================================

    def start_scan(self, profile, directory):

        return self.history_repo.create_scan(

            user=os.getenv("USER") or os.getenv("USERNAME") or "user",

            directory_scanned=str(directory or profile),

            start_time=datetime.now(),

            status="RUNNING"
        )

    # --------------------------------------------------

    def register_threat(
        self,
        scan_id: int,
        detected_file: DetectedFile,
        virus: Virus,
        action: str
    ):

        self.history_repo.add_threat(

            scan_id=scan_id,

            file_path=detected_file.path,

            virus_name=virus.name,

            action=action,

            detection_time=datetime.now()
        )

    # --------------------------------------------------

    def finish_scan(self, scan_id, total_files, infected_files):

        self.history_repo.finish_scan(

            scan_id=scan_id,

            total_files=total_files,

            infected_files=infected_files,

            end_time=datetime.now(),

            status="COMPLETED"
        )

    # --------------------------------------------------

    def mark_scan_failed(self, scan_id, reason):

        self.history_repo.update_status(

            scan_id=scan_id,

            status="FAILED_ENGINE",

            error_message=reason
        )

    # --------------------------------------------------

    def get_scan_history(self, limit=100):

        return self.history_repo.get_recent_scans(limit)

    # ==================================================
    # STATUS DO CLAMAV
    # ==================================================

    def get_status(self):
        """
        Retorna status do ClamAV através do serviço.
        """

        try:
            return self.clamav.get_status()
        except Exception:
            return "unknown"