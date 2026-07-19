from PyQt5.QtCore import QSettings


class ScanPreferencesService:
    """Persiste e aplica preferências relacionadas ao início do scan."""

    BROWSER_WARNING_KEY = "scan/warn_running_browsers"
    DEFAULT_BROWSER_WARNING = True
    WARNING_PROFILES = frozenset({"FULL", "CUSTOM"})

    def __init__(self, settings=None):
        self.settings = settings or QSettings(
            "AntivirusProject",
            "AntivirusProject",
        )

    def browser_warning_enabled(self):
        value = self.settings.value(
            self.BROWSER_WARNING_KEY,
            self.DEFAULT_BROWSER_WARNING,
        )
        if isinstance(value, str):
            return value.strip().casefold() not in {"0", "false", "no", "off"}
        return bool(value)

    def set_browser_warning_enabled(self, enabled):
        self.settings.setValue(self.BROWSER_WARNING_KEY, bool(enabled))
        self.settings.sync()

    def should_warn_for_scan(self, profile):
        return (
            str(profile or "").upper() in self.WARNING_PROFILES
            and self.browser_warning_enabled()
        )
