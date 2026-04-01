"""QSS stylesheet builder for the Digital Obsidian design system.

Takes theme token dicts and font strings, returns a complete QSS stylesheet
string for the entire PyQt6 application. All colors and spacing values come
from tokens — nothing is hardcoded.
"""


def build_qss(
    tokens: dict,
    font_body: str,
    font_mono: str,
    font_headline: str = "",
) -> str:
    """Build a complete QSS stylesheet from theme tokens and font stacks.

    Args:
        tokens: Dict of theme tokens (e.g. DARK_TOKENS or LIGHT_TOKENS).
        font_body: CSS font-family string for body text.
        font_mono: CSS font-family string for monospace/code text.
        font_headline: CSS font-family string for headlines (Manrope).

    Returns:
        A single QSS stylesheet string ready for QApplication.setStyleSheet().
    """
    t = tokens
    hl = font_headline or font_body
    return f"""
/* ===================================================================
   Digital Obsidian QSS — auto-generated from theme tokens
   =================================================================== */

/* ----- 1. Global base ----- */
/* NOTE: No background on QWidget — that kills tonal layering by painting
   bg-void on every child widget.  Backgrounds are set on specific named
   containers below so the surface hierarchy (void → surface → panel → cell)
   is visible. */
QWidget {{
    color: {t["text-primary"]};
    font-family: {font_body};
    font-size: 12px;
}}

/* Shell-level surfaces */
QMainWindow {{
    background: {t["bg-void"]};
}}

QDialog {{
    background: {t["bg-void"]};
    color: {t["text-primary"]};
}}

/* Content area — sits one tonal step above void */
QWidget#contentArea {{
    background: {t["surface-container-low"]};
}}

/* Stacked widget inside content area — transparent so parent bg shows */
QStackedWidget {{
    background: transparent;
}}

/* ----- 2. QPushButton default (secondary / ghost style) ----- */
QPushButton {{
    background: transparent;
    border: 1px solid {t["ghost-border"]};
    color: {t["text-primary"]};
    border-radius: {t["r-l"]};
    padding: 6px 16px;
}}

QPushButton:hover {{
    background: {t["bg-hover"]};
    color: {t["text-bright"]};
}}

QPushButton:pressed {{
    background: {t["bg-cell"]};
}}

/* ----- 3. QPushButton#btnPrimary — gradient CTA ----- */
QPushButton#btnPrimary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary"]}, stop:1 {t["primary-container"]});
    color: {t["text-on-cyan"]};
    border: none;
    border-radius: {t["r-l"]};
    padding: 8px 24px;
    font-weight: 700;
    font-size: 13px;
}}

QPushButton#btnPrimary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary-dim"]}, stop:1 {t["primary"]});
}}

QPushButton#btnPrimary:disabled {{
    background: {t["bg-selected"]};
    color: {t["text-muted"]};
}}

/* ----- 4. QPushButton#btnSecondary — ghost border ----- */
QPushButton#btnSecondary {{
    background: transparent;
    border: 1px solid {t["ghost-border"]};
    color: {t["text-primary"]};
    border-radius: {t["r-l"]};
    padding: 6px 16px;
}}

QPushButton#btnSecondary:hover {{
    background: {t["bg-hover"]};
    color: {t["text-bright"]};
}}

QPushButton#btnSecondary:pressed {{
    background: {t["bg-cell"]};
}}

/* ----- 5. QPushButton#btnDestructive ----- */
QPushButton#btnDestructive {{
    background: transparent;
    color: {t["error"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-l"]};
    padding: 6px 16px;
}}

QPushButton#btnDestructive:hover {{
    color: {t["error-dim"]};
    background: {t["bg-hover"]};
}}

/* ----- 5b. QPushButton[button_role] property selectors ----- */
QPushButton[button_role="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary"]}, stop:1 {t["primary-container"]});
    color: {t["text-on-cyan"]};
    border: none;
    border-radius: {t["r-l"]};
    padding: 8px 24px;
    font-weight: 700;
    font-size: 13px;
}}

QPushButton[button_role="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary-dim"]}, stop:1 {t["primary"]});
}}

QPushButton[button_role="primary"]:disabled {{
    background: {t["bg-selected"]};
    color: {t["text-muted"]};
}}

QPushButton[button_role="secondary"] {{
    background: transparent;
    border: 1px solid {t["ghost-border"]};
    color: {t["text-primary"]};
    border-radius: {t["r-l"]};
    padding: 6px 16px;
}}

QPushButton[button_role="secondary"]:hover {{
    background: {t["bg-hover"]};
    color: {t["text-bright"]};
}}

QPushButton[button_role="secondary"]:pressed {{
    background: {t["bg-cell"]};
}}

QPushButton[button_role="destructive"] {{
    background: transparent;
    color: {t["error"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-l"]};
    padding: 6px 16px;
}}

QPushButton[button_role="destructive"]:hover {{
    color: {t["error-dim"]};
    background: {t["bg-hover"]};
}}

QPushButton[button_role="cta"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary"]}, stop:1 {t["primary-container"]});
    color: {t["text-on-cyan"]};
    border: none;
    border-radius: {t["r-l"]};
    padding: 10px 28px;
    font-family: {hl};
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 1px;
}}

QPushButton[button_role="cta"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary-dim"]}, stop:1 {t["primary"]});
}}

QPushButton[button_role="cta"]:disabled {{
    background: {t["bg-selected"]};
    color: {t["text-muted"]};
}}

/* ----- 6. Focus states ----- */
QPushButton:focus,
QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus {{
    border: 1px solid {t["border-focus"]};
    outline: none;
}}

/* ----- 7. Input wells — QLineEdit, QTextEdit, QSpinBox, QComboBox ----- */
QLineEdit,
QTextEdit,
QPlainTextEdit,
QSpinBox,
QDoubleSpinBox,
QComboBox {{
    background: {t["input-well"]};
    border: 1px solid {t["ghost-border"]};
    color: {t["text-bright"]};
    border-radius: {t["r-m"]};
    padding: 7px 12px;
}}

QLineEdit:focus,
QTextEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus {{
    border: 1px solid {t["border-focus"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background: {t["bg-panel"]};
    border: 1px solid {t["ghost-border"]};
    selection-background-color: {t["bg-hover"]};
    color: {t["text-primary"]};
    border-radius: {t["r-m"]};
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
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-s"]};
    background: {t["input-well"]};
}}

QCheckBox::indicator:checked,
QRadioButton::indicator:checked {{
    background: {t["primary"]};
    border-color: {t["primary"]};
}}

/* ----- 9. QSlider ----- */
QSlider::groove:horizontal,
QSlider::groove:vertical {{
    background: {t["bg-surface"]};
    border-radius: {t["r-s"]};
}}

QSlider::groove:horizontal {{
    height: 4px;
}}

QSlider::groove:vertical {{
    width: 4px;
}}

QSlider::handle:horizontal,
QSlider::handle:vertical {{
    background: {t["primary"]};
    border-radius: 7px;
    width: 14px;
    height: 14px;
    margin: -5px 0;
}}

QSlider::sub-page:horizontal {{
    background: {t["primary-dim"]};
    border-radius: {t["r-s"]};
}}

/* ----- 10. QProgressBar ----- */
QProgressBar {{
    background: {t["bg-surface"]};
    border-radius: {t["r-s"]};
    border: none;
    text-align: center;
    color: transparent;
    min-height: 6px;
    max-height: 6px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t["primary"]}, stop:1 {t["secondary"]});
    border-radius: {t["r-s"]};
}}

/* ----- 11. QTableWidget, QTreeWidget — no gridlines, tonal hover ----- */
QTableWidget,
QTableView,
QTreeWidget,
QTreeView {{
    background: {t["bg-void"]};
    border: none;
    gridline-color: transparent;
    alternate-background-color: {t["bg-surface"]};
}}

QTableWidget::item,
QTableView::item,
QTreeWidget::item,
QTreeView::item {{
    padding: 6px 10px;
    border: none;
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
    padding: 8px 10px;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
}}

/* ----- 13. QScrollBar:vertical ----- */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    border: none;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {t["bg-cell"]};
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t["bg-hover"]};
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
    background: transparent;
    height: 6px;
    border: none;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {t["bg-cell"]};
    border-radius: 3px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {t["bg-hover"]};
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
    border: 1px solid {t["ghost-border"]};
    padding: 6px 10px;
    border-radius: {t["r-m"]};
}}

/* ----- 15. QWidget#sidebar — tonal surface, no border ----- */
QWidget#sidebar {{
    background: {t["bg-surface"]};
    border: none;
}}

/* Page widgets — transparent so contentArea bg shows through */
QWidget#pageRoot {{
    background: transparent;
}}

/* ----- 16. QPushButton#sidebarItem — tonal active, no left indicator ----- */
QPushButton#sidebarItem {{
    background: transparent;
    color: {t["text-dim"]};
    text-align: left;
    border: none;
    padding: 8px 12px;
    min-height: 32px;
    border-radius: {t["r-m"]};
    font-size: 12px;
}}

QPushButton#sidebarItem:checked {{
    background: {t["bg-cell"]};
    color: {t["primary"]};
    font-weight: 600;
}}

QPushButton#sidebarItem:hover:!checked {{
    background: {t["bg-hover"]};
    color: {t["text-primary"]};
}}

/* ----- 17. QLabel#sidebarSection ----- */
QLabel#sidebarSection {{
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    color: {t["text-muted"]};
    padding: 6px 12px 2px 12px;
    letter-spacing: 1px;
}}

/* ----- 18. QLabel#pageTitle — Manrope headline ----- */
QLabel#pageTitle {{
    color: {t["text-bright"]};
    font-family: {hl};
    font-size: 22px;
    font-weight: 800;
}}

/* ----- 19. QLabel#pageDescription ----- */
QLabel#pageDescription {{
    color: {t["text-dim"]};
    font-size: 12px;
}}

/* ----- 20. QWidget#logFeed ----- */
QWidget#logFeed {{
    background: {t["bg-panel"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-xl"]};
}}

/* ----- 21. QWidget#activityDrawer ----- */
QWidget#activityDrawer {{
    background: {t["bg-panel"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-xl"]};
}}

/* ----- 22. QWidget#dpanel (DataPanel) — tonal card with ghost border ----- */
QWidget#dpanel {{
    background: {t["bg-panel"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-xl"]};
}}

QWidget#dpanelHeader {{
    background: transparent;
}}

QWidget#dpanelBody {{
    background: transparent;
}}

QLabel#dpanelTitle {{
    color: {t["text-bright"]};
    font-family: {hl};
    font-weight: 700;
    font-size: 13px;
}}

/* ----- 23. QGroupBox ----- */
QGroupBox {{
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-l"]};
    color: {t["text-dim"]};
    margin-top: 16px;
    padding: 12px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding-left: 10px;
    padding-top: 2px;
    color: {t["text-dim"]};
}}

/* ----- 24. QTabWidget, QTabBar ----- */
QTabWidget::pane {{
    background: {t["bg-surface"]};
    border: none;
    border-radius: {t["r-l"]};
}}

QTabBar::tab {{
    background: transparent;
    color: {t["text-dim"]};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {t["primary"]};
    border-bottom: 2px solid {t["primary"]};
}}

QTabBar::tab:hover {{
    color: {t["text-primary"]};
    background: {t["bg-hover"]};
}}

/* ----- 25. QMenu ----- */
QMenu {{
    background: {t["bg-panel"]};
    color: {t["text-primary"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-m"]};
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: {t["r-s"]};
}}

QMenu::item:selected {{
    background: {t["bg-hover"]};
    color: {t["text-bright"]};
}}

/* ----- 26. QDialog — (handled in global section above) ----- */

/* ----- 27. QSplitter::handle ----- */
QSplitter::handle {{
    background: transparent;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:horizontal {{
    width: 2px;
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

QLabel#sectionLabel {{
    color: {t["text-bright"]};
    font-family: {hl};
    font-weight: 700;
    font-size: 13px;
}}

/* ----- 29. Data color properties ----- */
QLabel[dataColor="cyan"] {{
    color: {t["primary"]};
}}
QLabel[dataColor="green"] {{
    color: {t["secondary"]};
}}
QLabel[dataColor="orange"] {{
    color: {t["orange"]};
}}
QLabel[dataColor="red"] {{
    color: {t["error"]};
}}
QLabel[dataColor="dim"] {{
    color: {t["text-dim"]};
}}
QLabel[dataColor="muted"] {{
    color: {t["text-muted"]};
}}

/* ----- 30. QScrollArea & viewport ----- */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QAbstractScrollArea {{
    background: transparent;
}}

/* ----- 31. QStatusBar ----- */
QStatusBar {{
    background: {t["bg-surface"]};
    color: {t["text-muted"]};
    font-size: 10px;
    border: none;
}}

/* ----- 32. QListWidget ----- */
QListWidget {{
    background: {t["bg-void"]};
    border: none;
    border-radius: {t["r-m"]};
}}

QListWidget::item {{
    padding: 6px 10px;
    border: none;
    border-radius: {t["r-s"]};
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

/* ----- 34. Stat cards & status dots ----- */
QWidget#statCard {{
    background: {t["surface-container-highest"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-xl"]};
    padding: 8px 16px;
}}

QLabel#statValue {{
    color: {t["text-bright"]};
    font-family: {hl};
    font-size: 18px;
    font-weight: 700;
}}

QLabel#statLabel {{
    color: {t["text-muted"]};
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QLabel#statDot,
QLabel#statusDot {{
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
    background: {t["secondary"]};
}}

/* ----- 35. Status pills ----- */
QLabel#statusTag {{
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: {t["r-s"]};
}}

QLabel#statusTag[color="cyan"] {{
    color: {t["primary"]};
    border: 1px solid {t["primary"]};
}}

QLabel#statusTag[color="green"] {{
    color: {t["secondary"]};
    border: 1px solid {t["secondary"]};
}}

QLabel#statusTag[color="orange"] {{
    color: {t["orange"]};
    border: 1px solid {t["orange"]};
}}

QLabel#statusTag[color="red"] {{
    color: {t["error"]};
    border: 1px solid {t["error"]};
}}

/* ----- 36. Header bar ----- */
QWidget#headerBar {{
    background: {t["bg-void"]};
    border-bottom: 1px solid {t["ghost-border"]};
    min-height: 48px;
    max-height: 48px;
}}

QLabel#headerBrand {{
    color: {t["primary"]};
    font-family: {hl};
    font-size: 14px;
    font-weight: 800;
}}

QPushButton#headerTab {{
    background: transparent;
    color: {t["text-dim"]};
    border: none;
    padding: 4px 12px;
    border-radius: {t["r-m"]};
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#headerTab:checked {{
    color: {t["text-bright"]};
    background: {t["bg-cell"]};
}}

QPushButton#headerTab:hover:!checked {{
    color: {t["text-primary"]};
    background: {t["bg-hover"]};
}}

/* ----- 37. Status bar ----- */
QWidget#statusBar {{
    background: {t["bg-void"]};
    border-top: 1px solid {t["ghost-border"]};
    min-height: 28px;
    max-height: 32px;
}}

QLabel#statusBarText {{
    color: {t["text-muted"]};
    font-size: 10px;
}}

QLabel#statusBarMeta {{
    color: {t["text-muted"]};
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ----- 38. Sidebar branding ----- */
QLabel#appTitle {{
    color: {t["primary"]};
    font-family: {hl};
    font-size: 15px;
    font-weight: 800;
    padding: 0px 4px;
}}

QLabel#appSubtitle {{
    color: {t["text-muted"]};
    font-size: 10px;
    padding: 0px 4px;
}}

/* ----- 39. Sidebar CTA button ----- */
QPushButton#sidebarCta {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary"]}, stop:1 {t["primary-container"]});
    color: {t["text-on-cyan"]};
    border: none;
    border-radius: {t["r-m"]};
    padding: 8px 16px;
    font-family: {hl};
    font-weight: 700;
    font-size: 11px;
}}

QPushButton#sidebarCta:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary-dim"]}, stop:1 {t["primary"]});
}}

/* ----- 40. Collapsible section ----- */
QFrame#collapsibleSection {{
    background: transparent;
    border: none;
}}

QLabel#collapsibleTitle {{
    color: {t["text-bright"]};
    font-weight: 600;
    font-size: 12px;
}}

QPushButton#collapsibleToggle {{
    background: transparent;
    color: {t["text-dim"]};
    border: none;
    font-size: 12px;
}}

/* ----- 41. ConfigBar ----- */
QWidget#configBar {{
    background: {t["bg-panel"]};
    border: 1px solid {t["ghost-border"]};
    border-radius: {t["r-xl"]};
    padding: 4px 8px;
}}

QLabel#configLabel {{
    color: {t["text-muted"]};
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ----- 42. Split layout ----- */
QWidget#splitLayout {{
    background: transparent;
}}

QWidget#splitLeft,
QWidget#splitRight {{
    background: transparent;
}}

/* ----- 43. Empty state ----- */
QWidget#emptyState {{
    background: transparent;
}}

QLabel#emptyStateIcon {{
    font-size: 36px;
    color: {t["text-muted"]};
}}

QLabel#emptyStateTitle {{
    color: {t["text-dim"]};
    font-family: {hl};
    font-size: 16px;
    font-weight: 700;
}}

QLabel#emptyStateDesc {{
    color: {t["text-muted"]};
    font-size: 12px;
}}

/* ----- 44. Activity drawer ----- */
QPushButton#activityDrawerToggle {{
    background: transparent;
    color: {t["text-dim"]};
    border: none;
    font-weight: 600;
    font-size: 12px;
    text-align: left;
    padding: 4px 0px;
}}

QPushButton#activityDrawerToggle:hover {{
    color: {t["text-primary"]};
}}

QLabel#activityDrawerBadge {{
    color: {t["text-muted"]};
    font-size: 10px;
}}

/* ----- 45. Page header stats ----- */
QWidget#pageHeader {{
    background: transparent;
}}

/* ----- 46. Source folder bar ----- */
QWidget#sourceFolderBar {{
    background: transparent;
}}

/* ----- 47. Log entries ----- */
QLabel#logTimestamp {{
    color: {t["text-muted"]};
    font-family: {font_mono};
    font-size: 10px;
}}

QLabel#logMessage {{
    color: {t["text-primary"]};
    font-size: 11px;
}}
"""
