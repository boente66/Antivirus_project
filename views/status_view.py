from datetime import datetime

from PyQt5 import QtCore, QtWidgets

from controllers.status_controller import StatusController
from utils.icon_loader import get_icon
from views.components import CardFrame, FeatureCard, MetricCard


class StatusView(QtWidgets.QWidget):
    def __init__(
        self,
        parent=None,
        scan_controller=None,
        navigation=None,
    ):
        super().__init__(parent)
        self.scan_controller = scan_controller
        self.navigation = navigation or {}
        self.controller = StatusController()
        self._build_ui()
        self._connect_signals()
        self.refresh_status()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(14)

        self.card = CardFrame(object_name="HeroCard")
        hero = QtWidgets.QHBoxLayout(self.card)
        hero.setContentsMargins(24, 22, 24, 22)
        hero.setSpacing(22)

        icon_panel = QtWidgets.QFrame()
        icon_panel.setFixedSize(118, 118)
        icon_panel.setStyleSheet(
            "background:#EAF8F0;border:1px solid #C7EBD4;"
            "border-radius:59px;"
        )
        icon_layout = QtWidgets.QVBoxLayout(icon_panel)
        self.status_icon = QtWidgets.QLabel()
        self.status_icon.setAlignment(QtCore.Qt.AlignCenter)
        icon_layout.addWidget(self.status_icon)
        hero.addWidget(icon_panel, 0, QtCore.Qt.AlignVCenter)

        status_column = QtWidgets.QVBoxLayout()
        status_column.setSpacing(7)
        self.status_label = QtWidgets.QLabel("Verificando proteção...")
        self.status_label.setObjectName("PageTitle")
        self.engine_label = QtWidgets.QLabel("Consultando o ClamAV")
        self.engine_label.setProperty("muted", True)
        self.engine_label.setWordWrap(True)
        self.protection_detail = QtWidgets.QLabel(
            "Os módulos serão atualizados assim que a verificação de status terminar."
        )
        self.protection_detail.setProperty("muted", True)
        self.protection_detail.setWordWrap(True)
        status_column.addWidget(self.status_label)
        status_column.addWidget(self.engine_label)
        status_column.addWidget(self.protection_detail)
        status_column.addStretch()

        self.scan_btn = QtWidgets.QPushButton("Verificação Inteligente")
        self.scan_btn.setProperty("role", "primary")
        self.scan_btn.setIcon(get_icon("scan"))
        self.scan_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.scan_btn.setMinimumWidth(250)
        self.scan_btn.clicked.connect(self.run_scan)
        status_column.addWidget(self.scan_btn)
        hero.addLayout(status_column, 1)
        layout.addWidget(self.card)

        metrics = QtWidgets.QGridLayout()
        metrics.setSpacing(12)
        self.clamav_metric = MetricCard(
            "ClamAV",
            "Verificando",
            "Estado do mecanismo",
            "database",
            "green",
        )
        self.last_scan_metric = MetricCard(
            "Última verificação",
            "Nesta sessão: nenhuma",
            "O histórico completo permanece disponível",
            "history",
            "blue",
        )
        self.update_metric = MetricCard(
            "Status atualizado",
            "Agora",
            "Atualização desta tela",
            "update",
            "purple",
        )
        metrics.addWidget(self.clamav_metric, 0, 0)
        metrics.addWidget(self.last_scan_metric, 0, 1)
        metrics.addWidget(self.update_metric, 0, 2)
        layout.addLayout(metrics)

        self.features_layout = QtWidgets.QGridLayout()
        self.features_layout.setSpacing(12)
        feature_data = [
            (
                "Firewall",
                "Gerencie regras e acompanhe conexões.",
                "Abrir",
                "firewall",
                "firewall",
            ),
            (
                "Quarentena",
                "Revise arquivos isolados com segurança.",
                "Abrir",
                "quarantine",
                "quarantine",
            ),
            (
                "Histórico",
                "Consulte scans, ameaças e resultados.",
                "Abrir",
                "history",
                "history",
            ),
            (
                "Verificação personalizada",
                "Escolha diretórios específicos para analisar.",
                "Selecionar",
                "folder",
                "custom_scan",
            ),
        ]
        self.feature_cards = []
        for index, (title, description, action, icon, target) in enumerate(feature_data):
            card = FeatureCard(title, description, action, icon)
            callback = self.navigation.get(target)
            if callback:
                card.activated.connect(callback)
            else:
                card.action_button.setEnabled(False)
            self.feature_cards.append(card)
            self.features_layout.addWidget(card, 0, index)
        layout.addLayout(self.features_layout)
        layout.addStretch()

    def _connect_signals(self):
        self.controller.status_loaded.connect(self._on_status)
        self.controller.error.connect(self._on_error)
        if self.scan_controller is not None:
            self.scan_controller.scan_finished.connect(
                self._on_scan_session_finished
            )

    def refresh_status(self):
        try:
            self.status_label.setText("Verificando proteção...")
            self.engine_label.setText("Consultando o ClamAV")
            self.status_icon.setPixmap(get_icon("loading").pixmap(62, 62))
            self.controller.load_status()
        except Exception as exc:
            self._on_error(str(exc))

    def _on_status(self, data):
        try:
            protection = data.get("protection")
            engine = data.get("engine", "Desconhecido")
            active = protection == "active"

            self.status_label.setText(
                "Proteção ativa" if active else "Proteção requer atenção"
            )
            self.status_label.setStyleSheet(
                "color:#18A957;" if active else "color:#E53935;"
            )
            self.status_icon.setPixmap(
                get_icon("shield" if active else "warning").pixmap(62, 62)
            )
            self.engine_label.setText(f"ClamAV: {engine}")
            self.protection_detail.setText(
                "Os serviços essenciais reportaram funcionamento normal."
                if active
                else "Revise a conexão com o mecanismo de proteção."
            )
            self.clamav_metric.set_value(str(engine).capitalize())
            now = datetime.now().strftime("%H:%M")
            self.update_metric.set_value(f"Hoje, {now}")
        except Exception as exc:
            self._on_error(str(exc))

    def _on_scan_session_finished(self, _results):
        self.last_scan_metric.set_value(
            f"Hoje, {datetime.now().strftime('%H:%M')}"
        )
        self.last_scan_metric.set_detail("Verificação concluída nesta sessão")

    def _on_error(self, message):
        self.status_label.setText("Não foi possível atualizar o status")
        self.status_label.setStyleSheet("color:#E53935;")
        self.protection_detail.setText(str(message))
        self.status_icon.setPixmap(get_icon("warning").pixmap(62, 62))

    def run_scan(self):
        if not self.scan_controller:
            QtWidgets.QMessageBox.warning(
                self,
                "Verificação",
                "Controlador de scan não disponível.",
            )
            return

        try:
            self.scan_btn.setEnabled(False)
            self.scan_controller.start_smart_scan()
            QtCore.QTimer.singleShot(
                2000,
                lambda: self.scan_btn.setEnabled(True),
            )
        except Exception as exc:
            self.scan_btn.setEnabled(True)
            QtWidgets.QMessageBox.critical(
                self,
                "Erro ao iniciar verificação",
                str(exc),
            )

    def resizeEvent(self, event):
        columns = 2 if self.width() < 900 else 4
        for index, card in enumerate(self.feature_cards):
            self.features_layout.addWidget(
                card, index // columns, index % columns
            )
        super().resizeEvent(event)
