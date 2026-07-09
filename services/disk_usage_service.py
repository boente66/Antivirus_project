import os
import psutil
import heapq


class DiskUsageService:
    """
    Serviço responsável por análise de uso de disco.

    Funcionalidades:
    - listar volumes/discos do sistema
    - obter resumo de uso de disco
    - analisar diretórios
    - listar maiores arquivos
    """

    IGNORED_PATHS = (
        "/proc",
        "/sys",
        "/dev",
        "/run"
    )

    # =====================================================
    # LISTAR VOLUMES DO SISTEMA
    # =====================================================

    def get_volumes(self):

        volumes = []

        for part in psutil.disk_partitions(all=False):

            try:

                usage = psutil.disk_usage(part.mountpoint)

                volumes.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "filesystem": part.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })

            except PermissionError:
                continue

        return volumes

    # =====================================================
    # RESUMO DE UM DISCO ESPECÍFICO
    # =====================================================

    def get_disk_summary(self, mountpoint):

        if not os.path.exists(mountpoint):

            raise RuntimeError(
                f"Mountpoint inválido: {mountpoint}"
            )

        usage = psutil.disk_usage(mountpoint)

        return {
            "mountpoint": mountpoint,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent
        }

    # =====================================================
    # TAMANHO POR DIRETÓRIO (PRIMEIRO NÍVEL)
    # =====================================================

    def get_directory_breakdown(self, mountpoint):

        breakdown = []

        try:

            with os.scandir(mountpoint) as entries:

                for entry in entries:

                    if not entry.is_dir(follow_symlinks=False):
                        continue

                    path = entry.path

                    if path.startswith(self.IGNORED_PATHS):
                        continue

                    size = self._get_folder_size(path)

                    breakdown.append({
                        "name": entry.name,
                        "path": path,
                        "size": size
                    })

        except PermissionError:
            pass

        breakdown.sort(
            key=lambda x: x["size"],
            reverse=True
        )

        return breakdown

    # =====================================================
    # MAIORES ARQUIVOS
    # =====================================================

    def get_largest_files(self, mountpoint, limit=50):

        heap = []

        for root, dirs, filenames in os.walk(mountpoint):

            if root.startswith(self.IGNORED_PATHS):
                continue

            for name in filenames:

                file_path = os.path.join(root, name)

                try:

                    size = os.path.getsize(file_path)

                    if len(heap) < limit:

                        heapq.heappush(heap, (size, file_path))

                    else:

                        heapq.heappushpop(
                            heap,
                            (size, file_path)
                        )

                except (PermissionError, FileNotFoundError):
                    continue

        largest = []

        for size, path in sorted(
            heap,
            reverse=True
        ):

            largest.append({
                "name": os.path.basename(path),
                "path": path,
                "size": size
            })

        return largest

    # =====================================================
    # MÉTODO AUXILIAR
    # =====================================================

    def _get_folder_size(self, folder_path):

        total_size = 0

        try:

            for entry in os.scandir(folder_path):

                try:

                    if entry.is_file(follow_symlinks=False):

                        total_size += entry.stat().st_size

                    elif entry.is_dir(follow_symlinks=False):

                        total_size += self._get_folder_size(entry.path)

                except (PermissionError, FileNotFoundError):
                    continue

        except PermissionError:
            pass

        return total_size