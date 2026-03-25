"""QSS stylesheet builder for the zinc monochrome design system.

Takes theme token dicts and font strings, returns a complete QSS stylesheet
string for the entire PyQt6 application. All colors and spacing values come
from tokens — nothing is hardcoded.
"""


def build_qss(
    tokens: dict,
    font_body: str,
    font_mono: str,
) -> str:
    """Build a complete QSS stylesheet from theme tokens and font stacks.

    Args:
        tokens: Dict of theme tokens (e.g. DARK_TOKENS or LIGHT_TOKENS).
        font_body: CSS font-family string for body text.
        font_mono: CSS font-family string for monospace/code text.

    Returns:
        A single QSS stylesheet string ready for QApplication.setStyleSheet().
    """
    t = tokens
    return f"""
/* ===================================================================
   Zinc Monochrome QSS — auto-generated from theme tokens
   =================================================================== */

/* ----- 1. Global base (QWidget) ----- */
QWidget {{
    background: {t["bg-void"]};
    color: {t["text-primary"]};
    font-family: {font_body};
    font-size: 12px;
}}

/* ----- 2. QPushButton default (secondary style) ----- */
QPushButton {{
    background: transparent;
    border: 1px solid {t["border-hard"]};
    color: {t["text-primary"]};
    border-radius: {t["r-l"]};
    padding: 5px 14px;
}}

QPushButton:hover {{
    background: {t["bg-hover"]};
}}

QPushButton:pressed {{
    background: {t["bg-cell"]};
}}

/* ----- 3. QPushButton#btnPrimary ----- */
QPushButton#btnPrimary {{
    background: {t["accent-primary"]};
    color: {t["text-on-cyan"]};
    border: none;
    border-radius: {t["r-l"]};
    padding: 5px 18px;
    font-weight: 600;
}}

QPushButton#btnPrimary:hover {{
    background: {t["bg-hover"]};
    color: {t["text-bright"]};
}}

QPushButton#btnPrimary:disabled {{
    background: {t["bg-selected"]};
    opacity: 0.6;
}}

/* ----- 4. QPushButton#btnSecondary ----- */
QPushButton#btnSecondary {{
    background: transparent;
    border: 1px solid {t["border-hard"]};
    color: {t["text-primary"]};
    border-radius: {t["r-l"]};
    padding: 5px 14px;
}}

QPushButton#btnSecondary:hover {{
    background: {t["bg-hover"]};
}}

QPushButton#btnSecondary:pressed {{
    background: {t["bg-cell"]};
}}

/* ----- 5. QPushButton#btnDestructive ----- */
QPushButton#btnDestructive {{
    background: transparent;
    color: {t["red"]};
    border: 1px solid {t["border-hard"]};
    border-radius: {t["r-l"]};
    padding: 5px 14px;
}}

QPushButton#btnDestructive:hover {{
    color: {t["red-dim"]};
    background: {t["bg-hover"]};
}}

/* ----- 5b. QPushButton[button_role] property selectors ----- */
QPushButton[button_role="primary"] {{
    background: {t["accent-primary"]};
    color: {t["text-on-cyan"]};
    border: none;
    border-radius: {t["r-l"]};
    padding: 5px 18px;
    font-weight: 600;
}}

QPushButton[button_role="primary"]:hover {{
    background: {t["bg-hover"]};
    color: {t["text-bright"]};
}}

QPushButton[button_role="primary"]:disabled {{
    background: {t["bg-selected"]};
    opacity: 0.6;
}}

QPushButton[button_role="secondary"] {{
    background: transparent;
    border: 1px solid {t["border-hard"]};
    color: {t["text-primary"]};
    border-radius: {t["r-l"]};
    padding: 5px 14px;
}}

QPushButton[button_role="secondary"]:hover {{
    background: {t["bg-hover"]};
}}

QPushButton[button_role="secondary"]:pressed {{
    background: {t["bg-cell"]};
}}

QPushButton[button_role="destructive"] {{
    background: transparent;
    color: {t["red"]};
    border: 1px solid {t["border-hard"]};
    border-radius: {t["r-l"]};
    padding: 5px 14px;
}}

QPushButton[button_role="destructive"]:hover {{
    color: {t["red-dim"]};
    background: {t["bg-hover"]};
}}

/* ----- 6. Focus states ----- */
QPushButton:focus,
QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus,
QCheckBox:focus,
QRadioButton:focus,
QSlider:focus,
QTabBar::tab:focus {{
    border: 2px solid {t["border-focus"]};
    outline: none;
}}

/* ----- 7. QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox ----- */
QLineEdit,
QTextEdit,
QSpinBox,
QDoubleSpinBox,
QComboBox {{
    background: {t["bg-surface"]};
    border: 1px solid {t["border-hard"]};
    color: {t["text-primary"]};
    border-radius: {t["r-m"]};
    padding: 6px 10px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background: {t["bg-panel"]};
    border: 1px solid {t["border-hard"]};
    selection-background-color: {t["bg-hover"]};
    color: {t["text-primary"]};
}}

/* ----- 8. QCheckBox, QRadioButton ----- */
QCheckBox,
QRadioButton {{
    color: {t["text-primary"]};
    spacing: 8px;
}}

QCheckBox::indicator,
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t["border-bright"]};
    border-radius: {t["r-s"]};
    background: {t["bg-surface"]};
}}

QCheckBox::indicator:checked,
QRadioButton::indicator:checked {{
    background: {t["accent-primary"]};
    border-color: {t["accent-primary"]};
    image: url(:/icons/check-white.png);
}}

/* ----- 9. QSlider ----- */
QSlider::groove:horizontal,
QSlider::groove:vertical {{
    background: {t["bg-surface"]};
    border-radius: {t["r-s"]};
}}

QSlider::handle:horizontal,
QSlider::handle:vertical {{
    background: {t["accent-primary"]};
    border-radius: {t["r-m"]};
    width: 14px;
    height: 14px;
}}

/* ----- 10. QProgressBar ----- */
QProgressBar {{
    background: {t["bg-surface"]};
    border-radius: {t["r-s"]};
    border: none;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: {t["accent-primary"]};
    border-radius: {t["r-s"]};
}}

/* ----- 11. QTableWidget, QTreeWidget ----- */
QTableWidget,
QTableView,
QTreeWidget,
QTreeView {{
    background: {t["bg-void"]};
    border: 1px solid {t["border-hard"]};
    gridline-color: {t["border-soft"]};
}}

QTableWidget::item,
QTableView::item,
QTreeWidget::item,
QTreeView::item {{
    padding: 4px 8px;
}}

QTableWidget::item:selected,
QTableView::item:selected,
QTreeWidget::item:selected,
QTreeView::item:selected {{
    background: {t["bg-selected"]};
    color: {t["text-bright"]};
}}

QTableWidget::item:hover,
QTableView::item:hover,
QTreeWidget::item:hover,
QTreeView::item:hover {{
    background: {t["bg-hover"]};
}}

/* ----- 12. QHeaderView::section ----- */
QHeaderView::section {{
    background: {t["bg-surface"]};
    color: {t["text-dim"]};
    border: none;
    border-bottom: 1px solid {t["border-hard"]};
    padding: 6px;
}}

/* ----- 13. QScrollBar:vertical ----- */
QScrollBar:vertical {{
    background: {t["bg-void"]};
    width: 8px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: {t["bg-cell"]};
    border-radius: {t["r-s"]};
    min-height: 20px;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ----- 13b. QScrollBar:horizontal ----- */
QScrollBar:horizontal {{
    background: {t["bg-void"]};
    height: 8px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: {t["bg-cell"]};
    border-radius: {t["r-s"]};
    min-width: 20px;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
}}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ----- 14. QToolTip ----- */
QToolTip {{
    background: {t["bg-panel"]};
    color: {t["text-bright"]};
    border: 1px solid {t["border-hard"]};
    padding: 6px;
    border-radius: 0px;
}}

/* ----- 15. QWidget#sidebar ----- */
QWidget#sidebar {{
    background: {t["bg-surface"]};
    border-right: 1px solid {t["border-soft"]};
}}

/* ----- 16. QPushButton#sidebarItem ----- */
QPushButton#sidebarItem {{
    background: transparent;
    color: {t["text-dim"]};
    text-align: left;
    border: none;
    padding: 8px;
    min-height: 32px;
    border-radius: 0px;
}}

QPushButton#sidebarItem:checked {{
    background: {t["bg-cell"]};
    color: {t["text-bright"]};
    border-left: 2px solid {t["accent-primary"]};
}}

QPushButton#sidebarItem:hover:!checked {{
    background: {t["bg-hover"]};
}}

/* ----- 17. QLabel#sidebarSection ----- */
QLabel#sidebarSection {{
    font-size: 9px;
    text-transform: uppercase;
    color: {t["text-dim"]};
    padding: 4px 8px;
}}

/* ----- 18. QLabel#pageTitle ----- */
QLabel#pageTitle {{
    color: {t["text-bright"]};
    font-size: 18px;
    font-weight: 600;
}}

/* ----- 19. QLabel#pageDescription ----- */
QLabel#pageDescription {{
    color: {t["text-muted"]};
    font-size: 12px;
}}

/* ----- 20. QWidget#logFeed ----- */
QWidget#logFeed {{
    background: {t["bg-surface"]};
    border: 1px solid {t["border-hard"]};
}}

/* ----- 21. QWidget#activityDrawer ----- */
QWidget#activityDrawer {{
    background: {t["bg-surface"]};
    border-top: 1px solid {t["border-hard"]};
}}

/* ----- 22. QWidget#dpanel (DataPanel) ----- */
QWidget#dpanel {{
    background: {t["bg-surface"]};
    border: 1px solid {t["border-hard"]};
}}

/* ----- 23. QGroupBox ----- */
QGroupBox {{
    border: 1px solid {t["border-hard"]};
    border-radius: {t["r-m"]};
    color: {t["text-dim"]};
    margin-top: 16px;
    padding: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding-left: 8px;
    padding-top: 2px;
    color: {t["text-dim"]};
}}

/* ----- 24. QTabWidget, QTabBar ----- */
QTabWidget::pane {{
    background: {t["bg-surface"]};
    border: 1px solid {t["border-hard"]};
    border-radius: {t["r-m"]};
}}

QTabBar::tab {{
    background: transparent;
    color: {t["text-dim"]};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {t["text-bright"]};
    border-bottom: 2px solid {t["accent-primary"]};
}}

QTabBar::tab:hover {{
    color: {t["text-primary"]};
    background: {t["bg-hover"]};
}}

/* ----- 25. QMenu ----- */
QMenu {{
    background: {t["bg-panel"]};
    color: {t["text-primary"]};
    border: 1px solid {t["border-hard"]};
}}

QMenu::item:selected {{
    background: {t["bg-hover"]};
}}

/* ----- 26. QDialog ----- */
QDialog {{
    background: {t["bg-void"]};
    color: {t["text-primary"]};
}}

/* ----- 27. QSplitter::handle ----- */
QSplitter::handle {{
    background: {t["bg-surface"]};
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

/* ----- 28. Misc label helpers ----- */
QLabel#dimLabel {{
    color: {t["text-dim"]};
    font-size: 10px;
}}

QLabel#mutedLabel {{
    color: {t["text-muted"]};
    font-size: 10px;
}}

QLabel#boldLabel {{
    font-weight: bold;
    color: {t["text-bright"]};
}}

/* ----- 29. Data color properties ----- */
QLabel[dataColor="cyan"] {{
    color: {t["cyan"]};
}}
QLabel[dataColor="green"] {{
    color: {t["green"]};
}}
QLabel[dataColor="orange"] {{
    color: {t["orange"]};
}}
QLabel[dataColor="red"] {{
    color: {t["red"]};
}}
QLabel[dataColor="dim"] {{
    color: {t["text-dim"]};
}}
QLabel[dataColor="muted"] {{
    color: {t["text-muted"]};
}}

/* ----- 30. QScrollArea ----- */
QScrollArea {{
    background: transparent;
    border: none;
}}

/* ----- 31. QStatusBar ----- */
QStatusBar {{
    background: {t["bg-panel"]};
    color: {t["text-muted"]};
    font-size: 10px;
    border-top: 1px solid {t["border-hard"]};
}}

/* ----- 32. QListWidget ----- */
QListWidget {{
    background: {t["bg-void"]};
    border: 1px solid {t["border-hard"]};
}}

QListWidget::item {{
    padding: 4px 8px;
}}

QListWidget::item:selected {{
    background: {t["bg-selected"]};
    color: {t["text-bright"]};
}}

QListWidget::item:hover {{
    background: {t["bg-hover"]};
}}

/* ----- 33. Monospace text ----- */
QTextEdit#monoText {{
    font-family: {font_mono};
}}
"""
