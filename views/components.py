from PyQt5 import QtCore, QtWidgets

from utils.icon_loader import get_icon


class SectionHeader(QtWidgets.QWidget):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setObjectName("PageTitle")
        layout.addWidget(self.title_label)

        self.subtitle_label = QtWidgets.QLabel(subtitle)
        self.subtitle_label.setObjectName("PageSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        layout.addWidget(self.subtitle_label)


class CardFrame(QtWidgets.QFrame):
    def __init__(self, parent=None, object_name="Card"):
        super().__init__(parent)
        self.setObjectName(object_name)


class IconLabel(QtWidgets.QLabel):
    def __init__(self, icon_name, size=28, parent=None):
        super().__init__(parent)
        self.setFixedSize(size + 18, size + 18)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setPixmap(get_icon(icon_name).pixmap(size, size))
        self.setStyleSheet(
            "background:#EAF8F0;border-radius:%dpx;" % ((size + 18) // 2)
        )


class MetricCard(CardFrame):
    def __init__(
        self,
        title,
        value="—",
        detail="",
        icon="status",
        accent="green",
        parent=None,
    ):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 13, 14, 13)
        layout.setSpacing(12)

        self.icon_label = IconLabel(icon, 24)
        layout.addWidget(self.icon_label)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(2)
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setProperty("muted", True)
        self.value_label = QtWidgets.QLabel(str(value))
        self.value_label.setObjectName("MetricValue")
        self.value_label.setProperty("accent", accent)
        self.detail_label = QtWidgets.QLabel(detail)
        self.detail_label.setProperty("muted", True)
        self.detail_label.setWordWrap(True)
        self.detail_label.setVisible(bool(detail))
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.value_label)
        text_layout.addWidget(self.detail_label)
        layout.addLayout(text_layout, 1)

    def set_value(self, value):
        self.value_label.setText(str(value))

    def set_detail(self, detail):
        self.detail_label.setText(str(detail))
        self.detail_label.setVisible(bool(detail))


class FeatureCard(CardFrame):
    activated = QtCore.pyqtSignal()

    def __init__(
        self,
        title,
        description,
        action_text,
        icon="shield",
        state_text="",
        parent=None,
    ):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(9)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(IconLabel(icon, 30))
        text = QtWidgets.QVBoxLayout()
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("SectionTitle")
        description_label = QtWidgets.QLabel(description)
        description_label.setProperty("muted", True)
        description_label.setWordWrap(True)
        text.addWidget(title_label)
        text.addWidget(description_label)
        top.addLayout(text, 1)
        layout.addLayout(top)

        self.state_label = QtWidgets.QLabel(state_text)
        self.state_label.setStyleSheet("color:#108746;font-weight:600;")
        self.state_label.setVisible(bool(state_text))
        layout.addWidget(self.state_label)
        layout.addStretch()

        self.action_button = QtWidgets.QPushButton(action_text)
        self.action_button.setProperty("role", "secondary")
        self.action_button.clicked.connect(self.activated.emit)
        layout.addWidget(self.action_button)

    def set_state(self, text, color="#108746"):
        self.state_label.setText(str(text))
        self.state_label.setStyleSheet(f"color:{color};font-weight:600;")
        self.state_label.setVisible(bool(text))


class StateBadge(QtWidgets.QLabel):
    PALETTES = {
        "success": ("#108746", "#EAF8F0", "#BDE8CD"),
        "warning": ("#B56A00", "#FFF6E8", "#F7D79A"),
        "danger": ("#C62828", "#FFF0F0", "#F4C4C2"),
        "info": ("#1C64C7", "#EDF5FF", "#C7DEFA"),
        "neutral": ("#52637A", "#F1F4F6", "#DDE4EA"),
    }

    def __init__(self, text="", state="neutral", parent=None):
        super().__init__(text, parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.set_state(state)

    def set_state(self, state):
        foreground, background, border = self.PALETTES.get(
            state,
            self.PALETTES["neutral"],
        )
        self.setStyleSheet(
            f"color:{foreground};background:{background};"
            f"border:1px solid {border};border-radius:9px;"
            "padding:3px 9px;font-weight:700;"
        )


class EmptyState(CardFrame):
    def __init__(self, title, description, icon="shield", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 22)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setSpacing(8)
        layout.addWidget(IconLabel(icon, 34), 0, QtCore.Qt.AlignCenter)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("SectionTitle")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title_label)
        description_label = QtWidgets.QLabel(description)
        description_label.setProperty("muted", True)
        description_label.setAlignment(QtCore.Qt.AlignCenter)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)


def make_page_scroll(content, parent=None):
    scroll = QtWidgets.QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    scroll.setWidget(content)
    return scroll
