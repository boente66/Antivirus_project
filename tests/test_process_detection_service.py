import unittest
from unittest.mock import patch

import psutil

from core.platform.linux_adapter import LinuxAdapter
from services.process_detection_service import (
    BrowserProcessDetector,
    RunningBrowser,
)


class FakeAdapter:
    def __init__(self, processes=None, error=None):
        self.processes = processes or []
        self.error = error

    def get_running_processes(self):
        if self.error:
            raise self.error
        return self.processes


class ProcessWithInfoError:
    def __init__(self, error):
        self.error = error

    @property
    def info(self):
        raise self.error


class ProcessWithInfo:
    def __init__(self, pid, name):
        self.info = {"pid": pid, "name": name}


class BrowserProcessDetectorTests(unittest.TestCase):
    def test_no_browser_running(self):
        detector = BrowserProcessDetector(
            adapter=FakeAdapter([{"pid": 1, "name": "python"}])
        )
        self.assertEqual(detector.get_running_browsers(), [])

    def test_one_browser_running(self):
        detector = BrowserProcessDetector(
            adapter=FakeAdapter([{"pid": 10, "name": "firefox"}])
        )
        self.assertEqual(
            detector.get_running_browsers(),
            [RunningBrowser("Firefox", "firefox", 10)],
        )

    def test_multiple_browsers_running(self):
        detector = BrowserProcessDetector(
            adapter=FakeAdapter([
                {"pid": 30, "name": "brave-browser"},
                {"pid": 20, "name": "google-chrome"},
                {"pid": 40, "name": "not-a-browser"},
            ])
        )
        browsers = detector.get_running_browsers()
        self.assertEqual([item.display_name for item in browsers], [
            "Brave",
            "Google Chrome",
        ])
        self.assertEqual([item.pid for item in browsers], [30, 20])

    def test_configurable_process_names(self):
        detector = BrowserProcessDetector(
            adapter=FakeAdapter([{"pid": 50, "name": "company-browser"}]),
            browser_processes={"company-browser": "Navegador Corporativo"},
        )
        self.assertEqual(
            detector.get_running_browsers()[0].display_name,
            "Navegador Corporativo",
        )

    def test_multiple_processes_from_same_browser_are_deduplicated(self):
        detector = BrowserProcessDetector(
            adapter=FakeAdapter([
                {"pid": 102, "name": "chrome"},
                {"pid": 100, "name": "google-chrome"},
                {"pid": 101, "name": "chrome"},
            ])
        )
        self.assertEqual(
            detector.get_running_browsers(),
            [RunningBrowser("Google Chrome", "google-chrome", 100)],
        )

    def test_adapter_failure_is_not_propagated(self):
        detector = BrowserProcessDetector(
            adapter=FakeAdapter(error=psutil.AccessDenied(pid=99))
        )
        self.assertEqual(detector.get_running_browsers(), [])


class LinuxProcessEnumerationTests(unittest.TestCase):
    def test_access_denied_during_iteration(self):
        with patch(
            "core.platform.linux_adapter.psutil.process_iter",
            side_effect=psutil.AccessDenied(pid=1),
        ):
            self.assertEqual(LinuxAdapter().get_running_processes(), [])

    def test_process_ending_during_read(self):
        processes = [
            ProcessWithInfoError(psutil.NoSuchProcess(pid=2)),
            ProcessWithInfo(3, "firefox"),
        ]
        with patch(
            "core.platform.linux_adapter.psutil.process_iter",
            return_value=processes,
        ):
            self.assertEqual(
                LinuxAdapter().get_running_processes(),
                [{"pid": 3, "name": "firefox"}],
            )

    def test_no_such_process_does_not_abort_enumeration(self):
        processes = [ProcessWithInfoError(psutil.NoSuchProcess(pid=4))]
        with patch(
            "core.platform.linux_adapter.psutil.process_iter",
            return_value=processes,
        ):
            self.assertEqual(LinuxAdapter().get_running_processes(), [])


if __name__ == "__main__":
    unittest.main()
