import shutil
import platform


class FirewallDetector:
    """
    Detecta qual firewall o sistema operacional utiliza.
    """

    def detect(self):

        os_type = platform.system()

        if os_type == "Linux":

            if shutil.which("ufw"):
                return "ufw"

            if shutil.which("firewall-cmd"):
                return "firewalld"

            if shutil.which("iptables"):
                return "iptables"

            if shutil.which("nft"):
                return "nftables"

        elif os_type == "Windows":
            return "windows"

        elif os_type == "Darwin":
            return "pf"

        return "unknown"