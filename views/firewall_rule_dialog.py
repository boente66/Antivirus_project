from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)


class FirewallRuleDialog(QDialog):
    """Coleta dados da regra; validação de negócio permanece no Service."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar regra UFW")
        self.setModal(True)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Bloquear serviço local")
        self.action_input = QComboBox()
        self.action_input.addItem("Bloquear", "deny")
        self.action_input.addItem("Permitir", "allow")
        self.direction_input = QComboBox()
        self.direction_input.addItem("Entrada", "in")
        self.direction_input.addItem("Saída", "out")
        self.protocol_input = QComboBox()
        self.protocol_input.addItem("TCP", "tcp")
        self.protocol_input.addItem("UDP", "udp")
        self.port_start_input = QSpinBox()
        self.port_start_input.setRange(1, 65535)
        self.port_start_input.setValue(8080)
        self.port_end_input = QSpinBox()
        self.port_end_input.setRange(1, 65535)
        self.port_end_input.setValue(8080)
        self.source_input = QLineEdit("any")
        self.destination_input = QLineEdit("any")
        self.comment_input = QLineEdit()

        form.addRow("Nome", self.name_input)
        form.addRow("Ação", self.action_input)
        form.addRow("Direção", self.direction_input)
        form.addRow("Protocolo", self.protocol_input)
        form.addRow("Porta inicial", self.port_start_input)
        form.addRow("Porta final", self.port_end_input)
        form.addRow("Origem (IP/CIDR ou any)", self.source_input)
        form.addRow("Destino (IP/CIDR ou any)", self.destination_input)
        form.addRow("Comentário", self.comment_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self):
        return {
            "name": self.name_input.text(),
            "action": self.action_input.currentData(),
            "direction": self.direction_input.currentData(),
            "protocol": self.protocol_input.currentData(),
            "port_start": self.port_start_input.value(),
            "port_end": self.port_end_input.value(),
            "source": self.source_input.text(),
            "destination": self.destination_input.text(),
            "comment": self.comment_input.text(),
        }
