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

        result = self.clamav.scan_file(file_path)

        virus_name = None
        infected = False

        if result:

            infected = True

            try:
                virus_name = list(result.values())[0][1]
            except Exception:
                virus_name = "unknown"

        # -----------------------------
        # 2️⃣ File identification
        # -----------------------------

        file_info = self.identifier.identify(file_path)

        # -----------------------------
        # 3️⃣ Heuristic scoring
        # -----------------------------

        score = self.scorer.calculate(
            file_path=file_path,
            virus_name=virus_name,
            file_info=file_info
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

        if infected:

            detected = DetectedFile(path=file_path)
            virus = Virus(name=virus_name)

            return ScanResult(
                detected_file=detected,
                virus=virus,
                infected=True
            )

        return None