# services/filesystem_service.py

import os
import shutil
import glob
import platform
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

            if p == crit_p or crit_p in p.parents:
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

def _generate_quarantine_name(p: Path) -> Path:

    base = QUARANTINE_DIR / f"{p.name}_{abs(hash(str(p))) % 10000000}"

    target = base
    i = 1

    while target.exists():

        target = QUARANTINE_DIR / f"{base.name}_{i}"

        i += 1

    return target


def move_to_quarantine_single(path: str) -> str:

    try:

        p = Path(path).resolve()

        if not p.exists():
            return ""

        if is_critical(str(p)):
            return ""

        target = _generate_quarantine_name(p)

        shutil.move(str(p), str(target))

        return str(target)

    except Exception:
        return ""


def safe_move_to_quarantine(paths: Iterable[str]) -> List[str]:

    moved = []

    for p in paths:

        dest = move_to_quarantine_single(p)

        if dest:
            moved.append(dest)

    return moved


def safe_move_from_quarantine(source: str, destination: str) -> bool:

    try:

        src = Path(source).resolve()
        dst = Path(destination).resolve()

        if not src.exists():
            return False

        if is_critical(str(dst)):
            return False

        if not is_within_home(str(dst)):
            return False

        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src), str(dst))

        return True

    except Exception:
        return False


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