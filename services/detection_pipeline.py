from datetime import datetime

from models.detected_file import DetectedFile
from models.virus_model import Virus
from models.scan_result import ScanResult


class DetectionPipeline:

    def __init__(self, clamav, identifier, scorer):

        self.clamav = clamav
        self.identifier = identifier
        self.scorer = scorer

    def analyze(self, file_path):

        # -----------------------------
        # 1️⃣ Signature scan
        # -----------------------------

        clamav_result = self.clamav.scan_file(file_path)
        infected, virus_name = self._parse_clamav_result(clamav_result)

        # -----------------------------
        # 2️⃣ File identification
        # -----------------------------

        self.identifier.identify(file_path)

        # -----------------------------
        # 3️⃣ Heuristic scoring
        # -----------------------------

        score = self.scorer.calculate(
            file_path=file_path,
            virus_name=virus_name
        )

        # -----------------------------
        # 4️⃣ Heuristic fallback
        # -----------------------------

        if not infected and score >= 70:

            infected = True
            virus_name = "HEURISTIC_SUSPICIOUS_FILE"

        # -----------------------------
        # 5️⃣ Result
        # -----------------------------

        detected = DetectedFile(path=file_path)
        virus = Virus(
            name=virus_name or "",
            path=file_path,
            detection_date=datetime.now() if infected else None
        )

        return ScanResult(
            detected_file=detected,
            virus=virus,
            infected=infected,
            action=None
        )

    @staticmethod
    def _parse_clamav_result(result):
        """Converte a resposta do pyclamd sem mascarar respostas inválidas."""

        if not result:
            return False, None

        if not isinstance(result, dict):
            raise ValueError("Resposta inválida do ClamAV: esperado um dicionário.")

        try:
            status, detail = next(iter(result.values()))
        except (StopIteration, TypeError, ValueError) as exc:
            raise ValueError("Resposta inválida do ClamAV.") from exc

        if status == "FOUND":
            if not detail:
                raise ValueError("ClamAV detectou uma ameaça sem informar a assinatura.")

            return True, str(detail)

        if status == "OK":
            return False, None

        if status == "ERROR":
            reason = str(detail).strip() if detail else "motivo não informado"
            raise RuntimeError(f"ClamAV não concluiu a análise: {reason}")

        raise RuntimeError(f"ClamAV retornou status desconhecido: {status}")
