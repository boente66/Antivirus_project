# services/filesystem_service.py

import os
import shutil
import glob
import platform
from uuid import uuid4
from pathlib import Path
from typing import Iterable, List

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except Exception:
    HAS_SEND2TRASH = False


HOME = Path.home().resolve()
QUARANTINE_DIR = HOME / ".antivirus_quarantine"
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================
# CAMINHOS CRÍTICOS POR SISTEMA
# =====================================================

SYSTEM = platform.system()

LINUX_CRITICAL = {
    "/", "/bin", "/boot", "/dev", "/etc",
    "/lib", "/lib64", "/proc", "/root",
    "/sbin", "/sys", "/usr"
}

WINDOWS_CRITICAL = {
    "c:\\windows",
    "c:\\windows\\system32",
    "c:\\program files",
    "c:\\program files (x86)"
}

MAC_CRITICAL = {
    "/system",
    "/usr",
    "/bin",
    "/sbin",
    "/etc",
    "/var"
}

if SYSTEM == "Windows":
    CRITICAL_PATHS = WINDOWS_CRITICAL
elif SYSTEM == "Darwin":
    CRITICAL_PATHS = MAC_CRITICAL
else:
    CRITICAL_PATHS = LINUX_CRITICAL


# =====================================================
# UTILIDADES
# =====================================================

def _is_same_or_child(path: Path, parent: Path) -> bool:
    if path == parent:
        return True

    if parent.anchor == str(parent):
        return False

    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def expand_patterns(pattern: str) -> List[str]:

    if any(ch in pattern for ch in "*?[]"):

        return [
            str(Path(p).resolve())
            for p in glob.glob(pattern, recursive=True)
            if os.path.exists(p)
        ]

    p = Path(pattern).expanduser().resolve()

    return [str(p)] if p.exists() else []


def is_critical(path: str) -> bool:

    try:

        p = Path(path).resolve()

        for crit in CRITICAL_PATHS:

            crit_p = Path(crit).resolve()

            if _is_same_or_child(p, crit_p):
                return True

    except Exception:
        return True

    return False


def is_within_home(path: str) -> bool:

    try:

        p = Path(path).resolve()

        return HOME == p or HOME in p.parents

    except Exception:
        return False


# =====================================================
# TAMANHO
# =====================================================

def calculate_size(paths: Iterable[str]) -> int:

    total = 0

    for p in paths:

        try:

            pth = Path(p)

            if pth.is_file():

                total += pth.stat().st_size

            elif pth.is_dir():

                for root, _, files in os.walk(str(pth)):

                    for f in files:

                        try:

                            total += (Path(root) / f).stat().st_size

                        except Exception:
                            continue

        except Exception:
            continue

    return total


# =====================================================
# QUARENTENA
# =====================================================

def _resolve_absolute(path: str, operation: str) -> Path:
    candidate = Path(path).expanduser()

    if not candidate.is_absolute():
        raise ValueError(f"{operation}: caminho relativo não permitido: {path}")

    return candidate.resolve(strict=False)


def _quarantine_root(quarantine_dir=QUARANTINE_DIR) -> Path:
    root = Path(quarantine_dir).expanduser()

    if not root.is_absolute():
        raise ValueError(
            f"Quarentena: diretório relativo não permitido: {quarantine_dir}"
        )

    root.mkdir(parents=True, exist_ok=True)
    return root.resolve(strict=True)


def is_within_quarantine(path: str, quarantine_dir=QUARANTINE_DIR) -> bool:
    try:
        candidate = _resolve_absolute(path, "Quarentena")
        root = _quarantine_root(quarantine_dir)
        return candidate != root and candidate.is_relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False


def _generate_quarantine_name(p: Path, quarantine_dir=QUARANTINE_DIR) -> Path:
    root = _quarantine_root(quarantine_dir)

    while True:
        target = root / f"{uuid4().hex}_{p.name}"

        if not target.exists():
            return target


def move_to_quarantine_single(
    path: str,
    quarantine_dir=QUARANTINE_DIR
) -> str:
    source_input = Path(path).expanduser()

    if source_input.is_symlink():
        raise ValueError(
            f"Adicionar à quarentena: link simbólico não permitido: {path}"
        )

    source = _resolve_absolute(path, "Adicionar à quarentena")

    if not source.exists():
        raise FileNotFoundError(
            f"Adicionar à quarentena: arquivo não encontrado: {source}"
        )

    if not source.is_file():
        raise ValueError(
            f"Adicionar à quarentena: origem não é um arquivo: {source}"
        )

    if is_critical(str(source)):
        raise PermissionError(
            f"Adicionar à quarentena: caminho crítico bloqueado: {source}"
        )

    if is_within_quarantine(str(source), quarantine_dir):
        raise ValueError(
            f"Adicionar à quarentena: arquivo já está na quarentena: {source}"
        )

    target = _generate_quarantine_name(source, quarantine_dir)
    shutil.move(str(source), str(target))

    if source.exists() or not target.is_file():
        raise RuntimeError(
            f"Adicionar à quarentena: movimento não confirmado: "
            f"{source} -> {target}"
        )

    return str(target)


def safe_move_to_quarantine(
    paths: Iterable[str],
    quarantine_dir=QUARANTINE_DIR
) -> List[str]:

    moved = []

    for p in paths:

        moved.append(move_to_quarantine_single(p, quarantine_dir))

    return moved


def _available_restore_path(destination: Path) -> Path:
    if not destination.exists() and not destination.is_symlink():
        return destination

    for index in range(1, 10000):
        candidate = destination.with_name(
            f"{destination.stem}_restored_{index}{destination.suffix}"
        )

        if not candidate.exists() and not candidate.is_symlink():
            return candidate

    raise FileExistsError(
        f"Restaurar quarentena: não foi possível gerar nome alternativo para "
        f"{destination}"
    )


def safe_move_from_quarantine(
    source: str,
    destination: str,
    quarantine_dir=QUARANTINE_DIR,
    rename_on_conflict: bool = True
) -> str:
    source_input = Path(source).expanduser()

    if source_input.is_symlink():
        raise ValueError(
            f"Restaurar quarentena: link simbólico não permitido: {source}"
        )

    src = _resolve_absolute(source, "Restaurar quarentena")

    if not is_within_quarantine(str(src), quarantine_dir):
        raise PermissionError(
            f"Restaurar quarentena: origem fora da quarentena: {src}"
        )

    if not src.is_file():
        raise FileNotFoundError(
            f"Restaurar quarentena: arquivo não encontrado: {src}"
        )

    dst = _resolve_absolute(destination, "Restaurar quarentena")

    if is_within_quarantine(str(dst), quarantine_dir):
        raise PermissionError(
            f"Restaurar quarentena: destino dentro da quarentena: {dst}"
        )

    if is_critical(str(dst)):
        raise PermissionError(
            f"Restaurar quarentena: destino crítico bloqueado: {dst}"
        )

    if dst.exists() or dst.is_symlink():
        if not rename_on_conflict:
            raise FileExistsError(
                f"Restaurar quarentena: destino já existe: {dst}"
            )

        dst = _available_restore_path(dst)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst = dst.resolve(strict=False)

    if is_within_quarantine(str(dst), quarantine_dir):
        raise PermissionError(
            f"Restaurar quarentena: destino resolvido dentro da quarentena: {dst}"
        )

    shutil.move(str(src), str(dst))

    if src.exists() or not dst.is_file():
        raise RuntimeError(
            f"Restaurar quarentena: movimento não confirmado: {src} -> {dst}"
        )

    return str(dst)


def remove_quarantined_file(path: str, quarantine_dir=QUARANTINE_DIR) -> str:
    path_input = Path(path).expanduser()

    if path_input.is_symlink():
        raise ValueError(
            f"Excluir quarentena: link simbólico não permitido: {path}"
        )

    target = _resolve_absolute(path, "Excluir quarentena")

    if not is_within_quarantine(str(target), quarantine_dir):
        raise PermissionError(
            f"Excluir quarentena: caminho fora da quarentena: {target}"
        )

    if not target.exists():
        raise FileNotFoundError(
            f"Excluir quarentena: arquivo não encontrado: {target}"
        )

    if not target.is_file():
        raise ValueError(
            f"Excluir quarentena: caminho não é arquivo: {target}"
        )

    target.unlink()

    if target.exists():
        raise RuntimeError(
            f"Excluir quarentena: exclusão não confirmada: {target}"
        )

    return str(target)


# =====================================================
# REMOÇÃO
# =====================================================

def safe_remove(paths: Iterable[str]) -> List[str]:
    """
    Remoção permanente.
    Bloqueia diretórios críticos.
    """

    removed = []

    for p in paths:

        try:

            pth = Path(p).resolve()

            if not pth.exists():
                continue

            if is_critical(str(pth)):
                continue

            if pth.is_dir():

                shutil.rmtree(str(pth))

                removed.append(str(pth))

            elif pth.is_file():

                pth.unlink()

                removed.append(str(pth))

        except Exception:
            continue

    return removed


# =====================================================
# LIXEIRA
# =====================================================

def safe_send_to_trash(paths: Iterable[str]) -> List[str]:

    trashed = []

    for p in paths:

        try:

            pth = Path(p).resolve()

            if not pth.exists():
                continue

            if is_critical(str(pth)):
                continue

            if HAS_SEND2TRASH:

                send2trash(str(pth))

                trashed.append(str(pth))

            else:

                dest = move_to_quarantine_single(str(pth))

                if dest:
                    trashed.append(dest)

        except Exception:
            continue

    return trashed
