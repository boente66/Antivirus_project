# services/browser_detection_service.py

from pathlib import Path


class BrowserDetectionService:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, adapter):

        if adapter is None:
            raise ValueError("PlatformAdapter não informado")

        self.adapter = adapter

        self.home = Path.home()

    # =====================================================
    # DETECTA NAVEGADORES INSTALADOS
    # =====================================================

    def detect(self) -> dict:
        """
        Retorna estrutura:

        {
            "Firefox": {...},
            "Chrome": {...}
        }
        """

        browsers = {}

        paths = self._get_browser_paths()

        for name, path in paths.items():

            base = Path(path)

            if not base.exists():
                continue

            if name == "Firefox":

                browsers[name] = self._firefox_paths(base)

            else:

                browsers[name] = self._chrome_paths(base)

        return browsers

    # =====================================================
    # RETORNA TASKS PARA CLEANER
    # =====================================================

    def get_tasks(self, requested_categories: list[str]) -> list[dict]:

        browsers = self.detect()

        tasks = []

        for _, categories in browsers.items():

            for category, paths in categories.items():

                if category not in requested_categories:
                    continue

                tasks.append({
                    "action": "delete",
                    "paths": paths,
                    "requires_admin": False
                })

        return tasks

    # =====================================================
    # PATHS MULTIPLATAFORMA
    # =====================================================

    def _get_browser_paths(self):

        os_name = self.adapter.get_os_name()

        if os_name == "Linux":

            return {

                "Firefox": self.home / ".mozilla/firefox",

                "Chrome": self.home / ".config/google-chrome",

                "Chromium": self.home / ".config/chromium",

                "Brave": self.home / ".config/BraveSoftware/Brave-Browser"

            }

        if os_name == "Windows":

            base = Path(self.home / "AppData/Local")

            return {

                "Firefox": self.home / "AppData/Roaming/Mozilla/Firefox/Profiles",

                "Chrome": base / "Google/Chrome/User Data",

                "Edge": base / "Microsoft/Edge/User Data",

                "Brave": base / "BraveSoftware/Brave-Browser/User Data"

            }

        if os_name == "macOS":

            base = self.home / "Library/Application Support"

            return {

                "Firefox": base / "Firefox/Profiles",

                "Chrome": base / "Google/Chrome",

                "Edge": base / "Microsoft Edge",

                "Brave": base / "BraveSoftware/Brave-Browser"

            }

        return {}

    # =====================================================
    # FIREFOX
    # =====================================================

    def _firefox_paths(self, base: Path) -> dict:

        profiles = list(base.glob("*.default*"))

        return {

            "cache": [str(self.home / ".cache/mozilla/firefox")],

            "cookies": [str(p / "cookies.sqlite") for p in profiles],

            "history": [str(p / "places.sqlite") for p in profiles],

            "passwords": [str(p / "logins.json") for p in profiles],
        }

    # =====================================================
    # CHROME BASEADOS
    # =====================================================

    def _chrome_paths(self, base: Path) -> dict:

        return {

            "cache": [str(base / "Default/Cache")],

            "cookies": [str(base / "Default/Cookies")],

            "history": [str(base / "Default/History")],

            "passwords": [str(base / "Default/Login Data")],
        }