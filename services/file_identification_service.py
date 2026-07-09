import os
import stat
from pathlib import Path

try:
    import magic
    HAS_MAGIC = True
except Exception:
    HAS_MAGIC = False


class FileIdentificationService:

    MAX_ANALYZE_SIZE = 50 * 1024 * 1024  # 50MB

    EXEC_EXTENSIONS = (
        ".exe",
        ".dll",
        ".bin",
        ".run",
        ".appimage",
        ".com",
        ".scr"
    )

    SCRIPT_EXTENSIONS = (
        ".sh",
        ".py",
        ".js",
        ".php",
        ".pl",
        ".rb",
        ".ps1",
        ".bat"
    )

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def __init__(self):

        self.mime = None
        self.description = None

        if HAS_MAGIC:

            try:
                self.mime = magic.Magic(mime=True)
                self.description = magic.Magic()

            except Exception:
                self.mime = None
                self.description = None

    # --------------------------------------------------
    # Identificar arquivo
    # --------------------------------------------------

    def identify(self, file_path):

        result = {
            "path": file_path,
            "filename": "",
            "extension": "",
            "mime": None,
            "description": None,
            "size": 0,
            "suspicious": False,
            "executable": False,
            "script": False
        }

        try:

            p = Path(file_path).resolve()

            result["filename"] = p.name
            result["extension"] = p.suffix.lower()

            if not p.exists():
                return result

            # evitar links simbólicos
            if p.is_symlink():
                return result

            # evitar sockets / pipes
            mode = p.stat().st_mode

            if not stat.S_ISREG(mode):
                return result

            result["size"] = p.stat().st_size

            # evitar analisar arquivos muito grandes
            if result["size"] > self.MAX_ANALYZE_SIZE:
                return result

        except Exception:
            return result

        # --------------------------------
        # MIME / descrição
        # --------------------------------

        if self.mime and self.description:

            try:

                result["mime"] = self.mime.from_file(str(p))
                result["description"] = self.description.from_file(str(p))

            except Exception:
                pass

        # --------------------------------
        # Detectar executável
        # --------------------------------

        try:

            desc = (result["description"] or "").lower()

            if any(x in desc for x in (
                "executable",
                "elf",
                "pe32",
                "mach-o",
                "shared object"
            )):

                result["executable"] = True

        except Exception:
            pass

        # --------------------------------
        # Detectar scripts
        # --------------------------------

        if result["extension"] in self.SCRIPT_EXTENSIONS:

            result["script"] = True

        # --------------------------------
        # heurística simples
        # --------------------------------

        if result["executable"]:

            if result["extension"] not in self.EXEC_EXTENSIONS and result["extension"] != "":
                result["suspicious"] = True

        if result["script"] and result["extension"] not in self.SCRIPT_EXTENSIONS:
            result["suspicious"] = True

        return result