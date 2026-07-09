from services.clamav_service import ClamAVService


class SystemStatusService:

    def __init__(self):
        self.clamav = ClamAVService()

    def get_status(self):

        installed = self.clamav.is_installed()

        if not installed:
            return {
                "protection": "disabled",
                "engine": "not_installed"
            }

        try:
            status = self.clamav.get_status()
        except Exception:
            status = "stopped"

        return {
            "protection": "active" if status == "running" else "inactive",
            "engine": status
        }