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
        self.recovered_scan_count = (
            self.history_repo.recover_interrupted_scans(datetime.now())
        )

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
        return self.history_repo.start_scan(
            scan_type=profile,
            user=os.getenv("USER") or os.getenv("USERNAME") or "user",
            target=str(directory or profile),
            started_at=datetime.now(),
        )

    # --------------------------------------------------

    def register_threat(
        self,
        scan_id: int,
        detected_file: DetectedFile,
        virus: Virus,
        action: str
    ):

        return self.history_repo.add_threat(
            scan_id=scan_id,
            detected_file=detected_file,
            virus=virus,
            action=action,
            detection_date=virus.detection_date or datetime.now(),
        )

    def register_threats(self, scan_id, threats):
        return self.history_repo.add_threats(scan_id, threats)

    # --------------------------------------------------

    def finish_scan(
        self,
        scan_id,
        total_files,
        infected_files,
        status,
        error=None,
        treated_threats=0,
        failed_files=0,
    ):
        return self.history_repo.finish_scan(
            scan_id=scan_id,
            total_files=total_files,
            infected_files=infected_files,
            treated_threats=treated_threats,
            failed_files=failed_files,
            ended_at=datetime.now(),
            status=status,
            error=error,
        )

    # --------------------------------------------------

    def get_scan_history(self, filters=None, limit=50, offset=0):
        return self.history_repo.get_scans(
            filters=filters,
            limit=limit,
            offset=offset,
        )

    def get_scan_by_id(self, scan_id):
        return self.history_repo.get_scan_by_id(scan_id)

    def get_scan_threats(self, scan_id, limit=None, offset=0):
        return self.history_repo.get_threats_by_scan(
            scan_id,
            limit=limit,
            offset=offset,
        )

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
