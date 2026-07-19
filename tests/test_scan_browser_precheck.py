import os
import tempfile
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from controllers.scan_controller import ScanController
from services.process_detection_service import RunningBrowser
from services.scan_preferences_service import ScanPreferencesService
from views.scan_options_view import CustomScanView


class MemorySettings:
    def __init__(self):
        self.values = {}

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        pass


class ScanBrowserPrecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.settings = MemorySettings()
        self.preferences = ScanPreferencesService(self.settings)
        self.detector = Mock()
        self.scan_service = Mock(platform=Mock())
        self.controller = ScanController(
            scan_service=self.scan_service,
            process_detector=self.detector,
            preferences_service=self.preferences,
            quarantine_service=Mock(),
        )
        self.controller._start_scan = Mock(return_value=True)

    def test_scan_starts_normally_without_browser(self):
        self.detector.get_running_browsers.return_value = []
        self.assertTrue(self.controller.start_custom_scan("/tmp"))
        self.controller._start_scan.assert_called_once_with("CUSTOM", "/tmp")

    def test_scan_cancelled_after_warning(self):
        browser = RunningBrowser("Firefox", "firefox", 10)
        self.detector.get_running_browsers.return_value = [browser]
        warnings = []
        self.controller.browser_warning_requested.connect(warnings.append)

        self.assertFalse(self.controller.start_custom_scan("/tmp"))
        self.assertEqual(warnings, [[browser]])
        self.assertFalse(self.controller.resolve_browser_warning(False))
        self.controller._start_scan.assert_not_called()

    def test_scan_starts_after_confirmation(self):
        browser = RunningBrowser("Brave", "brave-browser", 11)
        self.detector.get_running_browsers.return_value = [browser]

        self.controller.start_custom_scan("/tmp")
        self.assertTrue(self.controller.resolve_browser_warning(True))
        self.controller._start_scan.assert_called_once_with("CUSTOM", "/tmp")

    def test_smart_scan_never_checks_processes(self):
        self.assertTrue(self.controller.start_smart_scan())
        self.detector.get_running_browsers.assert_not_called()
        self.controller._start_scan.assert_called_once_with("SMART", None)

    def test_disabled_preference_skips_custom_warning(self):
        self.preferences.set_browser_warning_enabled(False)
        self.assertTrue(self.controller.start_custom_scan("/tmp"))
        self.detector.get_running_browsers.assert_not_called()

    def test_do_not_show_again_is_persisted(self):
        self.detector.get_running_browsers.return_value = [
            RunningBrowser("Opera", "opera", 12)
        ]
        self.controller.start_custom_scan("/tmp")
        self.controller.resolve_browser_warning(True, dont_show_again=True)
        self.assertFalse(self.preferences.browser_warning_enabled())

    def test_full_profile_policy_is_ready(self):
        self.assertTrue(self.preferences.should_warn_for_scan("FULL"))
        self.preferences.set_browser_warning_enabled(False)
        self.assertFalse(self.preferences.should_warn_for_scan("FULL"))

    def test_preference_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.ini")
            first = ScanPreferencesService(
                QSettings(path, QSettings.IniFormat)
            )
            first.set_browser_warning_enabled(False)

            second = ScanPreferencesService(
                QSettings(path, QSettings.IniFormat)
            )
            self.assertFalse(second.browser_warning_enabled())

    def test_cancelled_precheck_does_not_open_progress_view(self):
        scan_controller = Mock()
        scan_controller.start_custom_scan.return_value = False
        parent_view = Mock()
        view = CustomScanView(scan_controller)
        view.parent_view = parent_view

        view.start_custom_scan()

        scan_controller.start_custom_scan.assert_called_once()
        parent_view.show_scan_view.assert_not_called()
        view.close()


if __name__ == "__main__":
    unittest.main()
