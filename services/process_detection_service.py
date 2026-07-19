import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from core.platform.platform_factory import PlatformFactory


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunningBrowser:
    display_name: str
    process_name: str
    pid: int


class BrowserProcessDetector:
    """Identifica navegadores entre os processos fornecidos pelo adapter."""

    DEFAULT_BROWSER_PROCESSES = {
        "google-chrome": "Google Chrome",
        "chrome": "Google Chrome",
        "chromium": "Chromium",
        "chromium-browser": "Chromium",
        "brave": "Brave",
        "brave-browser": "Brave",
        "firefox": "Firefox",
        "opera": "Opera",
        "opera-beta": "Opera Beta",
        "vivaldi": "Vivaldi",
        "microsoft-edge": "Microsoft Edge",
        "edge": "Microsoft Edge",
    }

    def __init__(
        self,
        adapter=None,
        browser_processes: Optional[Mapping[str, str]] = None,
    ):
        self.adapter = adapter or PlatformFactory.get_adapter()
        configured = browser_processes or self.DEFAULT_BROWSER_PROCESSES
        self.browser_processes = {
            self._normalize_process_name(name): str(display_name)
            for name, display_name in configured.items()
        }

    def get_running_browsers(self):
        try:
            processes = self.adapter.get_running_processes() or []
        except Exception as exc:
            logger.warning("Falha ao enumerar processos em execução: %s", exc)
            return []

        browsers_by_name = {}
        for process in processes:
            try:
                process_name = str(
                    process.get("name") or process.get("command") or ""
                ).strip()
                normalized = self._normalize_process_name(process_name)
                display_name = self.browser_processes.get(normalized)
                if not display_name:
                    continue

                browser = RunningBrowser(
                    display_name=display_name,
                    process_name=process_name,
                    pid=int(process.get("pid")),
                )
                current = browsers_by_name.get(display_name)
                if current is None or browser.pid < current.pid:
                    browsers_by_name[display_name] = browser
            except (AttributeError, TypeError, ValueError) as exc:
                logger.debug("Processo ignorado durante detecção: %s", exc)

        return sorted(
            browsers_by_name.values(),
            key=lambda browser: (
                browser.display_name.casefold(),
                browser.pid,
            ),
        )

    @staticmethod
    def _normalize_process_name(name):
        normalized = Path(str(name or "")).name.casefold()
        if normalized.endswith(".exe"):
            normalized = normalized[:-4]
        return normalized
