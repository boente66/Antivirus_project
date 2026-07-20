COLORS = {
    "navy": "#102536",
    "navy_alt": "#163247",
    "navy_hover": "#1D4056",
    "green": "#18A957",
    "green_dark": "#108746",
    "green_soft": "#EAF8F0",
    "blue": "#2878E6",
    "blue_soft": "#EDF5FF",
    "orange": "#F59E0B",
    "orange_soft": "#FFF6E8",
    "red": "#E53935",
    "red_soft": "#FFF0F0",
    "purple": "#7C4DDB",
    "purple_soft": "#F4EFFF",
    "ink": "#142033",
    "muted": "#617086",
    "border": "#DDE4EA",
    "surface": "#FFFFFF",
    "background": "#F4F7F9",
}


APP_STYLESHEET = """
QWidget {
    color: #142033;
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}

QMainWindow, QWidget#AppRoot, QFrame#ContentFrame {
    background: #F4F7F9;
}

QFrame#Sidebar {
    background: #102536;
    border: none;
}

QLabel#BrandTitle {
    color: white;
    font-size: 21px;
    font-weight: 700;
}

QLabel#BrandSubtitle, QLabel#SidebarCaption {
    color: #AFC0CE;
    font-size: 11px;
}

QPushButton[nav="true"] {
    background: transparent;
    color: #DCE7EE;
    border: none;
    border-radius: 8px;
    padding: 11px 12px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
}

QPushButton[nav="true"]:hover {
    background: #1D4056;
    color: white;
}

QPushButton[nav="true"]:checked {
    background: #174D46;
    color: #55E58C;
    border-left: 3px solid #2ED66F;
}

QFrame#SidebarStatus {
    background: #163247;
    border: 1px solid #315066;
    border-radius: 10px;
}

QLabel#SidebarStatusTitle {
    color: white;
    font-weight: 700;
}

QLabel#SidebarStatusText {
    color: #C8D6DF;
    font-size: 11px;
}

QLabel#PageTitle {
    color: #142033;
    font-size: 24px;
    font-weight: 700;
}

QLabel#PageSubtitle, QLabel[muted="true"] {
    color: #617086;
}

QLabel#SectionTitle {
    color: #142033;
    font-size: 16px;
    font-weight: 700;
}

QLabel#MetricValue {
    color: #142033;
    font-size: 22px;
    font-weight: 700;
}

QLabel#MetricValue[accent="green"] { color: #18A957; }
QLabel#MetricValue[accent="blue"] { color: #2878E6; }
QLabel#MetricValue[accent="orange"] { color: #F59E0B; }
QLabel#MetricValue[accent="red"] { color: #E53935; }
QLabel#MetricValue[accent="purple"] { color: #7C4DDB; }

QFrame#Card, QFrame[card="true"] {
    background: white;
    border: 1px solid #DDE4EA;
    border-radius: 12px;
}

QFrame#HeroCard {
    background: white;
    border: 1px solid #D7E4DC;
    border-radius: 14px;
}

QFrame#SuccessPanel {
    background: #EAF8F0;
    border: 1px solid #BDE8CD;
    border-radius: 10px;
}

QFrame#InfoPanel {
    background: #EDF5FF;
    border: 1px solid #C7DEFA;
    border-radius: 10px;
}

QFrame#WarningPanel {
    background: #FFF6E8;
    border: 1px solid #F7D79A;
    border-radius: 10px;
}

QPushButton {
    min-height: 34px;
    padding: 0 15px;
    border-radius: 7px;
    border: 1px solid #CCD6DE;
    background: white;
    color: #26364B;
    font-weight: 600;
}

QPushButton:hover {
    border-color: #18A957;
    color: #108746;
    background: #F7FCF9;
}

QPushButton:focus {
    border: 2px solid #2878E6;
}

QPushButton:disabled {
    color: #9DA9B4;
    background: #EFF2F4;
    border-color: #E0E5E9;
}

QPushButton[role="primary"] {
    color: white;
    background: #18A957;
    border-color: #18A957;
}

QPushButton[role="primary"]:hover {
    background: #108746;
    border-color: #108746;
    color: white;
}

QPushButton[role="danger"] {
    color: #D92D2A;
    background: white;
    border-color: #F08B88;
}

QPushButton[role="danger"]:hover {
    color: white;
    background: #E53935;
    border-color: #E53935;
}

QPushButton[role="secondary"] {
    color: #108746;
    background: white;
    border-color: #18A957;
}

QLineEdit, QComboBox, QDateEdit, QSpinBox {
    min-height: 34px;
    padding: 0 10px;
    background: white;
    border: 1px solid #CCD6DE;
    border-radius: 7px;
    selection-background-color: #18A957;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {
    border: 2px solid #2878E6;
}

QComboBox::drop-down {
    width: 28px;
    border: none;
}

QCheckBox {
    spacing: 9px;
    min-height: 24px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #AEBBC6;
    background: white;
}

QCheckBox::indicator:checked {
    background: #18A957;
    border-color: #18A957;
}

QProgressBar {
    min-height: 12px;
    max-height: 12px;
    border: none;
    border-radius: 6px;
    background: #E7ECEF;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: #18A957;
    border-radius: 6px;
}

QTableWidget, QListWidget, QTextEdit, QTreeWidget {
    background: white;
    border: 1px solid #DDE4EA;
    border-radius: 8px;
    alternate-background-color: #F8FAFB;
    selection-background-color: #EAF8F0;
    selection-color: #142033;
    outline: none;
}

QTableWidget::item, QListWidget::item {
    padding: 7px;
    border-bottom: 1px solid #EDF0F2;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background: #EAF8F0;
    color: #142033;
}

QHeaderView::section {
    background: #F5F8FA;
    color: #506178;
    border: none;
    border-bottom: 1px solid #DDE4EA;
    padding: 8px;
    font-weight: 700;
}

QTabWidget::pane {
    border: 1px solid #DDE4EA;
    background: white;
    border-radius: 9px;
    top: -1px;
}

QTabBar::tab {
    background: #F5F8FA;
    color: #52637A;
    min-height: 38px;
    min-width: 120px;
    padding: 0 14px;
    border: 1px solid #DDE4EA;
}

QTabBar::tab:selected {
    color: #108746;
    background: white;
    border-bottom: 3px solid #18A957;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #BEC9D1;
    border-radius: 5px;
    min-height: 28px;
}

QToolTip {
    color: #F7FAFC;
    background: #102536;
    border: 1px solid #315066;
    padding: 6px;
}

QDialog {
    background: #F4F7F9;
}
"""


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_button_role(button, role):
    button.setProperty("role", role)
    repolish(button)
