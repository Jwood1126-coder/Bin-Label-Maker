"""Avery template selector dropdown."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Signal

from src.models.avery_templates import AVERY_TEMPLATES, DEFAULT_TEMPLATE_ID


class AverySelector(QWidget):
    """Dropdown for selecting the Avery label template."""

    template_changed = Signal(str)  # emits template ID

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Avery Template:"))

        self._combo = QComboBox()
        for tid, geo in AVERY_TEMPLATES.items():
            label = f"{geo.name} ({geo.columns}x{geo.rows}, {geo.label_width}\"x{geo.label_height}\")"
            self._combo.addItem(label, tid)

        # Set default
        idx = self._combo.findData(DEFAULT_TEMPLATE_ID)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

        self._combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self._combo)

    def _on_changed(self, index: int) -> None:
        tid = self._combo.itemData(index)
        if tid:
            self.template_changed.emit(tid)

    def set_template_id(self, template_id: str) -> None:
        idx = self._combo.findData(template_id)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)
