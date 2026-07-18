from pathlib import Path


class BrowserDetectionService:
    """Localiza somente caches e cookies conhecidos de navegadores suportados."""

    def __init__(self, adapter):
        if adapter is None:
            raise ValueError("BrowserDetectionService: PlatformAdapter não informado.")
        self.adapter = adapter
        self.home = Path(adapter.get_home_directory()).expanduser().resolve()

    def detect(self):
        browsers = {}
        for name, base in self._get_browser_paths().items():
            if not base.exists():
                continue
            categories = (
                self._firefox_paths(base)
                if name == "Firefox"
                else self._chromium_paths(base)
            )
            browsers[name] = {
                category: [path for path in paths if Path(path).exists()]
                for category, paths in categories.items()
            }
        return browsers

    def get_tasks(self, requested):
        if not isinstance(requested, dict):
            raise ValueError("BrowserDetectionService: seleção inválida.")

        tasks = []
        detected = self.detect()
        for browser, categories in requested.items():
            available = detected.get(browser, {})
            for category in categories:
                paths = available.get(category, [])
                if not paths:
                    continue
                tasks.append({
                    "category": (
                        "browser_cache" if category == "cache" else "browser_cookies"
                    ),
                    "paths": list(paths),
                    "requires_admin": False,
                    "removal_mode": "permanent",
                    "browser": browser,
                })
        return tasks

    def _get_browser_paths(self):
        os_name = self.adapter.get_os_name()
        if os_name == "Linux":
            return {
                "Firefox": self.home / ".mozilla/firefox",
                "Chrome": self.home / ".config/google-chrome",
                "Chromium": self.home / ".config/chromium",
                "Brave": self.home / ".config/BraveSoftware/Brave-Browser",
                "Opera": self.home / ".config/opera",
            }
        if os_name == "Windows":
            local = self.home / "AppData/Local"
            return {
                "Firefox": self.home / "AppData/Roaming/Mozilla/Firefox/Profiles",
                "Chrome": local / "Google/Chrome/User Data",
                "Chromium": local / "Chromium/User Data",
                "Edge": local / "Microsoft/Edge/User Data",
                "Brave": local / "BraveSoftware/Brave-Browser/User Data",
                "Opera": self.home / "AppData/Roaming/Opera Software/Opera Stable",
            }
        if os_name == "macOS":
            base = self.home / "Library/Application Support"
            return {
                "Firefox": base / "Firefox/Profiles",
                "Chrome": base / "Google/Chrome",
                "Chromium": base / "Chromium",
                "Edge": base / "Microsoft Edge",
                "Brave": base / "BraveSoftware/Brave-Browser",
                "Opera": base / "com.operasoftware.Opera",
            }
        return {}

    def _firefox_paths(self, base):
        profiles = [path for path in base.glob("*.default*") if path.is_dir()]
        os_name = self.adapter.get_os_name()
        if os_name == "Linux":
            cache_base = self.home / ".cache/mozilla/firefox"
        elif os_name == "Windows":
            cache_base = self.home / "AppData/Local/Mozilla/Firefox/Profiles"
        else:
            cache_base = self.home / "Library/Caches/Firefox/Profiles"

        cache_paths = [
            str(path)
            for profile in cache_base.glob("*.default*")
            for path in (profile / "cache2", profile / "startupCache")
        ]
        return {
            "cache": cache_paths,
            "cookies": [str(profile / "cookies.sqlite") for profile in profiles],
        }

    @staticmethod
    def _chromium_paths(base):
        profiles = [base / "Default"]
        profiles.extend(path for path in base.glob("Profile *") if path.is_dir())
        cache_paths = []
        cookie_paths = []
        for profile in profiles:
            cache_paths.extend([
                str(profile / "Cache"),
                str(profile / "Code Cache"),
                str(profile / "GPUCache"),
            ])
            cookie_paths.extend([
                str(profile / "Network/Cookies"),
                str(profile / "Cookies"),
            ])
        return {"cache": cache_paths, "cookies": cookie_paths}
