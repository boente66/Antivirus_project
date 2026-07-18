import json
import os
import stat
import time
from datetime import datetime
from pathlib import Path

from database.entity.clean_entity import CleanEntity
from database.repositories.clean_history_repository import CleanHistoryRepository

try:
    from send2trash import send2trash as _send2trash
except ImportError:
    _send2trash = None

_DEFAULT_TRASH = object()


class CleanerService:
    """Analisa e remove somente alvos reconhecidos pela política do Cleaner."""

    STATUS_COMPLETED = "completed"
    STATUS_PARTIAL = "completed_with_failures"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_AUDIT_FAILED = "audit_failed"

    MODE_PERMANENT = "permanent"
    MODE_TRASH = "trash"

    USER_CATEGORIES = {
        "user_cache",
        "browser_cache",
        "browser_cookies",
        "trash",
    }
    TEMP_CATEGORIES = {"temporary", "system_temporary"}

    def __init__(
        self,
        adapter,
        repository=None,
        *,
        project_root=None,
        quarantine_dir=None,
        database_paths=None,
        trash_handler=_DEFAULT_TRASH,
    ):
        if adapter is None:
            raise ValueError("CleanerService: PlatformAdapter não informado.")

        self.adapter = adapter
        self.repository = repository or CleanHistoryRepository()
        self.home = Path(adapter.get_home_directory()).expanduser().resolve()
        self.project_root = Path(
            project_root or Path(__file__).resolve().parents[1]
        ).expanduser().resolve()
        self.quarantine_dir = Path(
            quarantine_dir or self.home / ".antivirus_quarantine"
        ).expanduser().resolve()
        self.database_paths = {
            Path(path).expanduser().resolve()
            for path in (database_paths or [self.project_root / "antivirus_system.db"])
        }
        self.trash_handler = (
            _send2trash if trash_handler is _DEFAULT_TRASH else trash_handler
        )

    def analyze(
        self,
        *,
        tasks,
        target_path=None,
        log_cb=None,
        progress_cb=None,
        should_stop=None,
    ):
        started = time.monotonic()
        normalized_tasks = self._validate_tasks(tasks)
        entries = self._expand_tasks(normalized_tasks)
        result = self._new_result("analysis", len(entries))

        for index, entry in enumerate(entries, start=1):
            if should_stop and should_stop():
                result["cancelled"] = True
                break

            outcome = self._analyze_entry(entry)
            result["processed"] += 1

            if outcome["state"] == "candidate":
                result["candidates"].append(outcome["item"])
                result["bytes_found"] += outcome["item"]["size"]
                self._log(log_cb, self._format_item_log("ANALYZE", outcome["item"], "candidate"))
            elif outcome["state"] == "ignored":
                result["ignored"] += 1
                self._log(log_cb, outcome["message"])
            else:
                result["failed"] += 1
                result["errors"].append(outcome["error"])
                self._log(log_cb, outcome["error"]["message"])

            self._progress(progress_cb, index, len(entries))

        result["duration_seconds"] = round(time.monotonic() - started, 3)
        result["status"] = self._final_status(result)
        return result

    def clean(
        self,
        *,
        tasks,
        target_path=None,
        require_admin=False,
        log_cb=None,
        progress_cb=None,
        should_stop=None,
    ):
        started = time.monotonic()
        analysis = self.analyze(
            tasks=tasks,
            target_path=target_path,
            log_cb=log_cb,
            progress_cb=None,
            should_stop=should_stop,
        )
        candidates = list(analysis["candidates"])
        result = self._new_result("clean", len(candidates))
        result["selected"] = analysis["selected"]
        result["ignored"] = analysis["ignored"]
        result["errors"].extend(analysis["errors"])
        result["failed"] = analysis["failed"]
        result["admin_required"] = any(
            item["requires_admin"] for item in candidates
        )

        if analysis["cancelled"] or (should_stop and should_stop()):
            result["cancelled"] = True
        else:
            for index, item in enumerate(candidates, start=1):
                if should_stop and should_stop():
                    result["cancelled"] = True
                    break

                result["processed"] += 1
                try:
                    current = self._revalidate_candidate(item)

                    if current["requires_admin"] and not require_admin:
                        raise PermissionError(
                            "item requer execução administrativa"
                        )

                    if require_admin and not self._has_admin():
                        raise PermissionError(
                            "processo elevado não possui privilégios administrativos"
                        )

                    removed_size, permanent = self._remove_candidate(current)
                    result["removed"] += 1
                    result["bytes_freed"] += removed_size
                    result["permanent"] = result["permanent"] or permanent
                    self._log(log_cb, self._format_item_log("CLEAN", current, "removed"))
                except FileNotFoundError as exc:
                    result["ignored"] += 1
                    self._append_error(result, item, "not_found", exc)
                except PermissionError as exc:
                    result["failed"] += 1
                    self._append_error(result, item, "permission_denied", exc)
                except (IsADirectoryError, NotADirectoryError) as exc:
                    result["failed"] += 1
                    self._append_error(result, item, "path_type_error", exc)
                except OSError as exc:
                    result["failed"] += 1
                    self._append_error(result, item, "filesystem_error", exc)
                except (RuntimeError, ValueError) as exc:
                    result["failed"] += 1
                    self._append_error(result, item, "operation_error", exc)

                self._progress(progress_cb, index, len(candidates))

        result["duration_seconds"] = round(time.monotonic() - started, 3)
        result["status"] = self._final_status(result)
        self._persist_result(result)
        return result

    def record_result(self, result):
        """Persiste resultados externos, como cancelamento de autenticação."""
        if not isinstance(result, dict):
            raise ValueError("CleanerService: resultado externo inválido.")
        self._persist_result(result)
        return result

    def _validate_tasks(self, tasks):
        if not isinstance(tasks, (list, tuple)) or not tasks:
            raise ValueError("CleanerService: nenhuma tarefa válida informada.")

        normalized = []
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                raise ValueError(f"CleanerService: tarefa {index} inválida.")

            category = str(task.get("category") or "").strip()
            paths = task.get("paths")
            mode = task.get("removal_mode", self.MODE_PERMANENT)

            if category not in self.USER_CATEGORIES | self.TEMP_CATEGORIES:
                raise ValueError(
                    f"CleanerService: categoria não permitida: {category or '<vazia>'}"
                )
            if not isinstance(paths, (list, tuple)) or not paths:
                raise ValueError(
                    f"CleanerService: tarefa '{category}' sem caminhos."
                )
            if mode not in (self.MODE_PERMANENT, self.MODE_TRASH):
                raise ValueError(
                    f"CleanerService: modo de remoção inválido: {mode}"
                )

            normalized.append({
                "category": category,
                "paths": tuple(str(path) for path in paths),
                "requires_admin": bool(task.get("requires_admin", False)),
                "removal_mode": mode,
                "browser": task.get("browser"),
            })

        return tuple(normalized)

    def _expand_tasks(self, tasks):
        entries = []
        for task in tasks:
            for raw_path in task["paths"]:
                path = Path(raw_path).expanduser()
                if not path.is_absolute():
                    entries.append({**task, "path": raw_path, "invalid": "relative_path"})
                    continue

                raw = path
                if raw.is_symlink():
                    entries.append({**task, "path": str(raw), "expand_root": False})
                    continue

                resolved = raw.resolve(strict=False)
                if self._is_container_root(resolved, task["category"]):
                    try:
                        children = sorted(resolved.iterdir(), key=lambda item: item.name)
                    except (FileNotFoundError, PermissionError, OSError):
                        children = [resolved]

                    entries.extend(
                        {**task, "path": str(child), "expand_root": True}
                        for child in children
                    )
                else:
                    entries.append({**task, "path": str(raw), "expand_root": False})

        return entries

    def _analyze_entry(self, entry):
        raw_path = Path(entry["path"]).expanduser()
        if entry.get("invalid"):
            return self._error_outcome(entry, "blocked", "caminho relativo bloqueado")

        try:
            is_link = raw_path.is_symlink()
            path = raw_path.absolute() if is_link else raw_path.resolve(strict=False)
            allowed_root = self._allowed_root(path, entry["category"], is_link)
            if allowed_root is None:
                return self._error_outcome(entry, "blocked", "caminho fora da política permitida")
            if self._is_protected(path):
                return self._error_outcome(entry, "blocked", "caminho protegido pelo aplicativo")
            if is_link:
                target = raw_path.resolve(strict=False)
                if not self._same_or_child(target, allowed_root):
                    return self._error_outcome(entry, "blocked_symlink", "link aponta para fora da raiz autorizada")
            elif not path.exists():
                return {"state": "ignored", "message": f"ANALYZE | {path} | ausente"}
            elif path.is_dir():
                invalid_link = self._find_external_symlink(path, allowed_root)
                if invalid_link is not None:
                    return self._error_outcome(
                        entry,
                        "blocked_symlink",
                        f"diretório contém link externo: {invalid_link}",
                    )
            if entry["category"] == "browser_cookies" and self._browser_running(entry.get("browser")):
                return self._error_outcome(entry, "browser_running", "navegador em execução; banco de cookies preservado")
            if not self._owned_or_admin(path, entry["requires_admin"]):
                return self._error_outcome(entry, "ownership", "item pertence a outro usuário")

            item = {
                "category": entry["category"],
                "path": str(raw_path.absolute() if is_link else path),
                "size": self._calculate_size(path, is_link=is_link),
                "requires_admin": entry["requires_admin"],
                "removal_mode": entry["removal_mode"],
                "kind": "symlink" if is_link else ("directory" if path.is_dir() else "file"),
                "browser": entry.get("browser"),
            }
            return {"state": "candidate", "item": item}
        except (PermissionError, OSError) as exc:
            return self._error_outcome(entry, "analysis_error", str(exc))

    def _revalidate_candidate(self, item):
        entry = {
            "category": item["category"],
            "path": item["path"],
            "requires_admin": item["requires_admin"],
            "removal_mode": item["removal_mode"],
            "browser": item.get("browser"),
        }
        outcome = self._analyze_entry(entry)
        if outcome["state"] == "ignored":
            raise FileNotFoundError(item["path"])
        if outcome["state"] != "candidate":
            raise PermissionError(outcome["error"]["message"])
        return outcome["item"]

    def _allowed_root(self, path, category, is_link=False):
        candidate = path.parent.resolve(strict=False) if is_link else path
        roots = []
        if category in self.TEMP_CATEGORIES:
            roots.extend(self._temp_roots())
        if category in self.USER_CATEGORIES:
            roots.extend(self._user_roots(category))

        matches = [root for root in roots if self._same_or_child(candidate, root)]
        return max(matches, key=lambda root: len(root.parts)) if matches else None

    def _temp_roots(self):
        roots = []
        for raw in self.adapter.get_temp_directories() or []:
            if raw:
                roots.append(Path(raw).expanduser().resolve(strict=False))
        return tuple(roots)

    def _user_roots(self, category):
        if category == "trash":
            return (
                self.home / ".local/share/Trash/files",
                self.home / ".Trash",
            )
        if category == "user_cache":
            return (self.home / ".cache",)
        if category in {"browser_cache", "browser_cookies"}:
            return (
                self.home / ".cache",
                self.home / ".mozilla/firefox",
                self.home / ".config/google-chrome",
                self.home / ".config/chromium",
                self.home / ".config/BraveSoftware/Brave-Browser",
                self.home / ".config/opera",
                self.home / "AppData/Local",
                self.home / "AppData/Roaming/Mozilla/Firefox/Profiles",
                self.home / "Library/Caches",
                self.home / "Library/Application Support",
            )
        return ()

    def _is_container_root(self, path, category):
        roots = self._temp_roots() if category in self.TEMP_CATEGORIES else self._user_roots(category)
        return any(path == root.resolve(strict=False) for root in roots)

    def _is_protected(self, path):
        application_paths = {
            self.project_root,
            self.project_root / ".git",
            self.project_root / ".venv",
            self.quarantine_dir,
            *self.database_paths,
        }
        application_paths.update(
            database.with_name(f"{database.name}{suffix}")
            for database in self.database_paths
            for suffix in ("-wal", "-shm")
        )
        for target in application_paths:
            resolved = target.resolve(strict=False)
            if path == resolved or self._same_or_child(path, resolved):
                return True

        system_paths = {
            Path(raw).expanduser().resolve(strict=False)
            for raw in (self.adapter.get_system_directories() or [])
            if raw
        }
        in_authorized_temp = any(
            self._same_or_child(path, root)
            for root in self._temp_roots()
        )
        for resolved in system_paths:
            if resolved == Path(resolved.anchor):
                if path == resolved:
                    return True
                continue
            if path == resolved or self._same_or_child(path, resolved):
                if in_authorized_temp:
                    continue
                return True
        return False

    def _remove_candidate(self, item):
        path = Path(item["path"])
        is_link = path.is_symlink()
        size = self._calculate_size(path, is_link=is_link)
        mode = item["removal_mode"]

        if mode == self.MODE_TRASH:
            if self.trash_handler is None:
                raise RuntimeError("send2trash indisponível; remoção permanente não executada")
            try:
                self.trash_handler(str(path))
            except Exception as exc:
                raise OSError(f"falha ao enviar para lixeira: {exc}") from exc
            if path.exists() or path.is_symlink():
                raise OSError("lixeira não confirmou a remoção do item")
            return size, False

        if is_link or path.is_file():
            path.unlink()
        elif path.is_dir():
            self._remove_directory(path)
        else:
            raise FileNotFoundError(str(path))
        if path.exists() or path.is_symlink():
            raise OSError("remoção permanente não confirmada")
        return size, True

    def _remove_directory(self, path):
        for entry in os.scandir(path):
            child = Path(entry.path)
            if entry.is_symlink():
                child.unlink()
            elif entry.is_dir(follow_symlinks=False):
                self._remove_directory(child)
            else:
                child.unlink()
        path.rmdir()

    def _find_external_symlink(self, directory, allowed_root):
        for entry in os.scandir(directory):
            child = Path(entry.path)
            if entry.is_symlink():
                if not self._same_or_child(child.resolve(strict=False), allowed_root):
                    return child
            elif entry.is_dir(follow_symlinks=False):
                invalid = self._find_external_symlink(child, allowed_root)
                if invalid is not None:
                    return invalid
        return None

    def _calculate_size(self, path, *, is_link=False):
        if is_link:
            return path.lstat().st_size
        if path.is_file():
            return path.stat().st_size
        if not path.is_dir():
            return 0

        total = 0
        for entry in os.scandir(path):
            child = Path(entry.path)
            if entry.is_symlink():
                total += child.lstat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += self._calculate_size(child)
            else:
                total += child.stat().st_size
        return total

    def _owned_or_admin(self, path, requires_admin):
        if requires_admin:
            return True
        if os.name == "nt":
            return self._same_or_child(path.resolve(strict=False), self.home)
        try:
            return path.lstat().st_uid == os.geteuid()
        except AttributeError:
            return self._same_or_child(path.resolve(strict=False), self.home)

    def _browser_running(self, browser):
        if not browser:
            return False
        names = {
            "firefox": ("firefox",),
            "chrome": ("chrome", "google-chrome"),
            "chromium": ("chromium",),
            "brave": ("brave",),
            "edge": ("msedge", "microsoft edge"),
            "opera": ("opera",),
        }.get(str(browser).lower(), ())
        try:
            processes = self.adapter.get_running_processes() or []
        except (OSError, RuntimeError):
            return False
        for process in processes:
            text = str(process.get("name") or process.get("command") or "").lower()
            if any(name in text for name in names):
                return True
        return False

    def _has_admin(self):
        return bool(self.adapter.has_admin_privileges())

    def _persist_result(self, result):
        entity = CleanEntity(
            user=os.getenv("USER") or os.getenv("USERNAME") or "unknown",
            timestamp=datetime.now().isoformat(),
            total_items=result["removed"],
            total_size=result["bytes_freed"],
            permanent=result["permanent"],
            details=json.dumps(result, ensure_ascii=False, sort_keys=True),
        )
        try:
            self.repository.insert(entity)
            result["history_id"] = entity.id
        except Exception as exc:
            result["audit_error"] = f"Falha ao persistir histórico: {exc}"
            result["errors"].append({
                "path": None,
                "category": "history",
                "code": "repository_error",
                "message": result["audit_error"],
            })
            result["status"] = self.STATUS_AUDIT_FAILED

    def _new_result(self, operation, selected):
        return {
            "operation": operation,
            "status": self.STATUS_COMPLETED,
            "selected": selected,
            "processed": 0,
            "removed": 0,
            "ignored": 0,
            "failed": 0,
            "bytes_found": 0,
            "bytes_freed": 0,
            "cancelled": False,
            "permanent": False,
            "admin_required": False,
            "candidates": [],
            "errors": [],
            "duration_seconds": 0.0,
            "history_id": None,
            "audit_error": None,
        }

    def _final_status(self, result):
        if result["cancelled"]:
            return self.STATUS_CANCELLED
        if result["failed"] or result["errors"]:
            if result["operation"] == "clean" and result["removed"] == 0:
                return self.STATUS_FAILED
            if result["operation"] == "analysis" and not result["candidates"]:
                return self.STATUS_FAILED
            return self.STATUS_PARTIAL
        return self.STATUS_COMPLETED

    def _append_error(self, result, item, code, exc):
        error = {
            "path": item.get("path"),
            "category": item.get("category"),
            "code": code,
            "message": f"CLEAN | {item.get('category')} | {item.get('path')} | {exc}",
        }
        result["errors"].append(error)

    def _error_outcome(self, entry, code, message):
        error = {
            "path": str(entry.get("path")),
            "category": entry.get("category"),
            "code": code,
            "message": f"ANALYZE | {entry.get('category')} | {entry.get('path')} | {message}",
        }
        return {"state": "error", "error": error}

    @staticmethod
    def _same_or_child(path, parent):
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    @staticmethod
    def _progress(callback, processed, total):
        if callback:
            callback(int((processed / max(total, 1)) * 100))

    @staticmethod
    def _log(callback, message):
        if callback:
            callback(message)

    @staticmethod
    def _format_item_log(operation, item, result):
        return (
            f"{operation} | {item['category']} | {item['path']} | "
            f"{result} | {item['size']} bytes"
        )
