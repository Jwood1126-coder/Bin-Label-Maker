"""Brennan Industries brand theme for the application UI.

Colors sourced from https://brennaninc.com/ brand guidelines.
"""
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPolygon
from PySide6.QtCore import QPoint

# ── Brand Colors ────────────────────────────────────────────
BRENNAN_BLUE = "#006293"
BRENNAN_BLUE_DARK = "#004E76"
BRENNAN_BLUE_LIGHT = "#1F7AAD"
BRENNAN_BLUE_HOVER = "#007BB5"
BRENNAN_GRAY = "#C7C8CA"
BRENNAN_GRAY_LIGHT = "#F0F2F4"
BRENNAN_GRAY_DARK = "#333333"
BRENNAN_WHITE = "#FFFFFF"
BRENNAN_BLACK = "#1A1A1A"
BRENNAN_RED = "#CC3333"

# ── Asset Paths ─────────────────────────────────────────────

def _assets_dir() -> Path:
    """Resolve the assets directory, works for dev and PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent.parent.parent / "assets"


def logo_full_path() -> str:
    return str(_assets_dir() / "brennan_logo_full.png")


def logo_icon_path() -> str:
    return str(_assets_dir() / "brennan_icon.png")


def logo_label_path() -> str:
    """Logo for printing on labels — small circle 'bi' icon."""
    return str(_assets_dir() / "brennan_icon.png")


def app_icon() -> QIcon:
    path = logo_icon_path()
    if os.path.exists(path):
        return QIcon(path)
    return QIcon()


def _combo_arrow_path() -> str:
    """Generate a small down-arrow PNG for QComboBox and return its path.

    Qt QSS doesn't support CSS border-triangle tricks, so we draw a proper
    arrow pixmap at startup and reference it via image: url(...).
    """
    arrow_dir = os.path.join(tempfile.gettempdir(), "bin_label_maker_assets")
    os.makedirs(arrow_dir, exist_ok=True)
    arrow_path = os.path.join(arrow_dir, "combo_arrow.png")
    if os.path.isfile(arrow_path):
        return arrow_path.replace("\\", "/")

    pix = QPixmap(12, 8)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(BRENNAN_BLUE))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(QPolygon([QPoint(1, 1), QPoint(11, 1), QPoint(6, 7)]))
    painter.end()
    pix.save(arrow_path, "PNG")
    return arrow_path.replace("\\", "/")


# ── Global Stylesheet ───────────────────────────────────────

STYLESHEET = f"""
/* ── Global ─────────────────────────────────────────── */
QMainWindow {{
    background-color: {BRENNAN_GRAY_LIGHT};
}}

QWidget {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {BRENNAN_BLACK};
}}

/* ── Menu Bar ───────────────────────────────────────── */
QMenuBar {{
    background-color: {BRENNAN_BLUE};
    color: {BRENNAN_WHITE};
    padding: 2px 0px;
    font-weight: 500;
}}

QMenuBar::item {{
    background: transparent;
    padding: 6px 14px;
    border-radius: 0px;
}}

QMenuBar::item:selected {{
    background-color: {BRENNAN_BLUE_HOVER};
}}

QMenu {{
    background-color: {BRENNAN_WHITE};
    border: 1px solid {BRENNAN_GRAY};
    padding: 4px 0px;
}}

QMenu::item {{
    padding: 6px 30px 6px 20px;
    color: {BRENNAN_BLACK};
}}

QMenu::item:selected {{
    background-color: {BRENNAN_BLUE};
    color: {BRENNAN_WHITE};
}}

QMenu::separator {{
    height: 1px;
    background: {BRENNAN_GRAY};
    margin: 4px 8px;
}}

/* ── Status Bar ─────────────────────────────────────── */
QStatusBar {{
    background-color: {BRENNAN_BLUE_DARK};
    color: {BRENNAN_WHITE};
    padding: 3px 8px;
    font-size: 12px;
}}

QStatusBar QLabel {{
    color: {BRENNAN_WHITE};
    font-size: 12px;
}}

/* ── Group Boxes ────────────────────────────────────── */
QGroupBox {{
    background-color: {BRENNAN_WHITE};
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 6px;
    margin-top: 14px;
    padding: 12px 10px 8px 10px;
    font-weight: 600;
    font-size: 13px;
    color: {BRENNAN_BLUE};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    background-color: {BRENNAN_WHITE};
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 4px;
    color: {BRENNAN_BLUE};
    font-weight: 600;
}}

/* ── Buttons ────────────────────────────────────────── */
QPushButton {{
    background-color: {BRENNAN_BLUE};
    color: {BRENNAN_WHITE};
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 500;
    font-size: 12px;
    min-height: 24px;
}}

QPushButton:hover {{
    background-color: {BRENNAN_BLUE_HOVER};
}}

QPushButton:pressed {{
    background-color: {BRENNAN_BLUE_DARK};
}}

QPushButton:disabled {{
    background-color: {BRENNAN_GRAY};
    color: #999999;
}}

/* Secondary / outline buttons */
QPushButton[cssClass="secondary"] {{
    background-color: {BRENNAN_WHITE};
    color: {BRENNAN_BLUE};
    border: 1px solid {BRENNAN_BLUE};
}}

QPushButton[cssClass="secondary"]:hover {{
    background-color: {BRENNAN_GRAY_LIGHT};
}}

QPushButton[cssClass="danger"] {{
    background-color: {BRENNAN_RED};
    color: {BRENNAN_WHITE};
}}

QPushButton[cssClass="danger"]:hover {{
    background-color: #AA2222;
}}

/* ── Spin Boxes ────────────────────────────────────── */
QSpinBox {{
    background-color: {BRENNAN_WHITE};
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
    min-height: 22px;
}}

QSpinBox:focus {{
    border: 2px solid {BRENNAN_BLUE};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 20px;
    border: none;
    background: transparent;
}}

/* ── Line Edits / Inputs ────────────────────────────── */
QLineEdit {{
    background-color: {BRENNAN_WHITE};
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    selection-background-color: {BRENNAN_BLUE};
    selection-color: {BRENNAN_WHITE};
}}

QLineEdit:focus {{
    border: 2px solid {BRENNAN_BLUE};
    padding: 4px 7px;
}}

QLineEdit:disabled {{
    background-color: {BRENNAN_GRAY_LIGHT};
    color: #999999;
}}

/* ── Combo Boxes ────────────────────────────────────── */
QComboBox {{
    background-color: {BRENNAN_WHITE};
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    min-height: 22px;
}}

QComboBox:focus {{
    border: 2px solid {BRENNAN_BLUE};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: url({{COMBO_ARROW_PATH}});
    width: 12px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {BRENNAN_WHITE};
    border: 1px solid {BRENNAN_GRAY};
    selection-background-color: {BRENNAN_BLUE};
    selection-color: {BRENNAN_WHITE};
    outline: none;
}}

/* ── Tables ─────────────────────────────────────────── */
QTableWidget {{
    background-color: {BRENNAN_WHITE};
    alternate-background-color: {BRENNAN_GRAY_LIGHT};
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 4px;
    gridline-color: #E0E0E0;
    selection-background-color: {BRENNAN_BLUE};
    selection-color: {BRENNAN_WHITE};
    font-size: 12px;
}}

QTableWidget::item {{
    padding: 4px 6px;
}}

QTableWidget::item:selected {{
    background-color: {BRENNAN_BLUE};
    color: {BRENNAN_WHITE};
}}

QHeaderView::section {{
    background-color: {BRENNAN_BLUE_DARK};
    color: {BRENNAN_WHITE};
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {BRENNAN_BLUE};
    font-weight: 600;
    font-size: 12px;
}}

/* ── Scroll Bars ────────────────────────────────────── */
QScrollBar:vertical {{
    background: {BRENNAN_GRAY_LIGHT};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {BRENNAN_GRAY};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {BRENNAN_BLUE_LIGHT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {BRENNAN_GRAY_LIGHT};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {BRENNAN_GRAY};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {BRENNAN_BLUE_LIGHT};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Splitter ───────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BRENNAN_GRAY};
    width: 3px;
}}

QSplitter::handle:hover {{
    background-color: {BRENNAN_BLUE};
}}

/* ── Graphics View (preview) ────────────────────────── */
QGraphicsView {{
    background-color: #E8EDF0;
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 4px;
}}

/* ── Dialogs ────────────────────────────────────────── */
QDialog {{
    background-color: {BRENNAN_GRAY_LIGHT};
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Checkboxes ─────────────────────────────────────── */
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BRENNAN_GRAY};
    border-radius: 3px;
    background: {BRENNAN_WHITE};
}}

QCheckBox::indicator:checked {{
    background-color: {BRENNAN_BLUE};
    border-color: {BRENNAN_BLUE};
}}

/* ── Tool Tips ──────────────────────────────────────── */
QToolTip {{
    background-color: {BRENNAN_BLUE_DARK};
    color: {BRENNAN_WHITE};
    border: none;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ── List Widgets ───────────────────────────────────── */
QListWidget {{
    background-color: {BRENNAN_WHITE};
    alternate-background-color: {BRENNAN_GRAY_LIGHT};
    border: 1px solid {BRENNAN_GRAY};
    border-radius: 4px;
    outline: none;
}}

QListWidget::item {{
    padding: 4px 8px;
}}

QListWidget::item:selected {{
    background-color: {BRENNAN_BLUE};
    color: {BRENNAN_WHITE};
}}

/* ── Section Headers (custom class) ─────────────────── */
QLabel[cssClass="section-header"] {{
    font-size: 14px;
    font-weight: 700;
    color: {BRENNAN_BLUE};
    padding: 4px 0px;
}}

QLabel[cssClass="brand-subtitle"] {{
    font-size: 11px;
    color: {BRENNAN_GRAY_DARK};
    font-weight: 400;
}}
"""


def get_stylesheet() -> str:
    """Return the stylesheet with the combo arrow image path resolved.

    Must be called after QApplication is created (needs QPainter).
    """
    arrow = _combo_arrow_path()
    return STYLESHEET.replace("{COMBO_ARROW_PATH}", arrow)
