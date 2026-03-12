"""Avery template selector dropdown."""
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Signal

from src.models.avery_templates import AVERY_TEMPLATES, DEFAULT_TEMPLATE_ID


class AverySelector(QComboBox):
    """Dropdown for selecting the Avery label template.

    Now a plain QComboBox (no wrapper widget with internal label)
    so it integrates cleanly with QFormLayout row labels.
    """

    template_changed = Signal(str)  # emits template ID

    def __init__(self, parent=None):
        super().__init__(parent)

        for tid, geo in AVERY_TEMPLATES.items():
            label = (
                f"{geo.name} ({geo.columns}x{geo.rows}, "
                f"{geo.label_width}\"x{geo.label_height}\")"
            )
            self.addItem(label, tid)

        # Set default
        idx = self.findData(DEFAULT_TEMPLATE_ID)
        if idx >= 0:
            self.setCurrentIndex(idx)

        self.currentIndexChanged.connect(self._on_changed)

    def _on_changed(self, index: int) -> None:
        tid = self.itemData(index)
        if tid:
            self.template_changed.emit(tid)

    def set_template_id(self, template_id: str) -> None:
        idx = self.findData(template_id)
        if idx >= 0:
            self.setCurrentIndex(idx)
