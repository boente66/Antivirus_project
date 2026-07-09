import os


class HeuristicService:

    SUSPICIOUS_EXTENSIONS = (
        ".sh",
        ".py",
        ".js",
        ".exe",
        ".bin",
        ".run"
    )

    SUSPICIOUS_LOCATIONS = (
        "/tmp",
        "/var/tmp",
        "/dev/shm"
    )

    def analyze(self, file_path):

        result = {
            "suspicious": False,
            "reason": None
        }

        path = file_path.lower()

        # -------------------------
        # extensão suspeita
        # -------------------------
        if path.endswith(self.SUSPICIOUS_EXTENSIONS):
            result["suspicious"] = True
            result["reason"] = "SUSPICIOUS_SCRIPT"
            return result

        # -------------------------
        # localização suspeita
        # -------------------------
        for loc in self.SUSPICIOUS_LOCATIONS:
            if path.startswith(loc):
                result["suspicious"] = True
                result["reason"] = "SUSPICIOUS_LOCATION"
                return result

        # -------------------------
        # executável oculto
        # -------------------------
        name = os.path.basename(path)

        if name.startswith(".") and os.access(file_path, os.X_OK):
            result["suspicious"] = True
            result["reason"] = "HIDDEN_EXECUTABLE"
            return result

        return result