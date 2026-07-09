from services.disk_usage_service import DiskUsageService
from core.platform.platform_factory import PlatformFactory


class DiskUsageController:
    """
    Controller responsável por intermediar a comunicação
    entre a interface (View) e o serviço de uso de disco.
    """

    # -------------------------------------------------
    # INIT
    # -------------------------------------------------

    def __init__(self):

        self.service = DiskUsageService()

        # adapter do sistema operacional
        self.adapter = PlatformFactory.create()

    # =====================================================
    # LISTAR TODOS OS DISCOS / VOLUMES
    # =====================================================

    def get_volumes(self):

        try:

            volumes = self.service.get_volumes()

            return volumes

        except Exception as e:

            raise RuntimeError(
                f"Erro ao obter volumes: {e}"
            )

    # =====================================================
    # RESUMO DE UM DISCO
    # =====================================================

    def get_volume_summary(self, mountpoint):

        try:

            if not self.validate_mountpoint(mountpoint):

                raise RuntimeError(
                    f"Volume inválido: {mountpoint}"
                )

            return self.service.get_disk_summary(mountpoint)

        except Exception as e:

            raise RuntimeError(
                f"Erro ao obter resumo do disco: {e}"
            )

    # =====================================================
    # DIRETÓRIOS QUE MAIS OCUPAM ESPAÇO
    # =====================================================

    def get_directory_breakdown(self, mountpoint):

        try:

            if not self.validate_mountpoint(mountpoint):

                raise RuntimeError(
                    f"Volume inválido: {mountpoint}"
                )

            return self.service.get_directory_breakdown(mountpoint)

        except Exception as e:

            raise RuntimeError(
                f"Erro ao analisar diretórios: {e}"
            )

    # =====================================================
    # MAIORES ARQUIVOS
    # =====================================================

    def get_largest_files(self, mountpoint, limit=50):

        try:

            if not self.validate_mountpoint(mountpoint):

                raise RuntimeError(
                    f"Volume inválido: {mountpoint}"
                )

            return self.service.get_largest_files(mountpoint, limit)

        except Exception as e:

            raise RuntimeError(
                f"Erro ao listar arquivos: {e}"
            )

    # =====================================================
    # VALIDAR VOLUME
    # =====================================================

    def validate_mountpoint(self, mountpoint):

        try:

            volumes = self.get_volumes()

            for v in volumes:

                if v["mountpoint"] == mountpoint:

                    return True

        except Exception:
            pass

        return False

    # =====================================================
    # UTILITÁRIO PARA UI (CONVERTER TAMANHO)
    # =====================================================

    def format_size(self, size):

        for unit in ["B", "KB", "MB", "GB", "TB"]:

            if size < 1024:
                return f"{size:.2f} {unit}"

            size /= 1024

        return f"{size:.2f} PB"

    # =====================================================
    # PERCENTUAL DE USO
    # =====================================================

    def get_volume_percent(self, mountpoint):

        summary = self.get_volume_summary(mountpoint)

        return summary.get("percent", 0)
