import psutil


class ProcessMonitor:
    """
    Responsável por monitorar processos do sistema.

    Pode ser usado para:
        - listar processos ativos
        - detectar processos suspeitos
        - finalizar processos
    """

    # --------------------------------------------------
    # listar processos
    # --------------------------------------------------

    def list_processes(self):

        processes = []

        for proc in psutil.process_iter(
            ['pid', 'name', 'username', 'cpu_percent', 'memory_percent']
        ):

            try:

                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "user": proc.info['username'],
                    "cpu": proc.info['cpu_percent'],
                    "memory": proc.info['memory_percent']
                })

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return processes

    # --------------------------------------------------
    # obter informações de um processo
    # --------------------------------------------------

    def get_process_info(self, pid):

        try:

            proc = psutil.Process(pid)

            return {
                "pid": pid,
                "name": proc.name(),
                "exe": proc.exe(),
                "cpu": proc.cpu_percent(),
                "memory": proc.memory_percent(),
                "status": proc.status()
            }

        except Exception:

            return None

    # --------------------------------------------------
    # finalizar processo
    # --------------------------------------------------

    def kill_process(self, pid):

        try:

            proc = psutil.Process(pid)

            proc.terminate()

            return True

        except Exception:

            return False

    # --------------------------------------------------
    # detectar processos suspeitos
    # --------------------------------------------------

    def detect_suspicious_processes(self):

        suspicious = []

        for proc in psutil.process_iter(
            ['pid', 'name', 'cpu_percent', 'memory_percent']
        ):

            try:

                cpu = proc.info['cpu_percent']
                mem = proc.info['memory_percent']

                # critérios simples
                if cpu > 80 or mem > 80:

                    suspicious.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu": cpu,
                        "memory": mem
                    })

            except Exception:
                pass

        return suspicious