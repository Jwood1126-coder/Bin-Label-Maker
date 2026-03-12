"""QPixmap-based preview renderer for the GUI.

Renders the same layout as the PDF renderer but onto a QImage
for display in the preview panel.
"""
import logging
from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPixmap, QPen
from PySide6.QtWidgets import QApplication

from src.models.avery_templates import AveryGeometry, AVERY_TEMPLATES
from src.models.template import Template
from src.models.label_data import LabelData
from src.services.label_layout import LabelLayoutService, CellLayout
from src.services.qr_generator import QRGenerator
from src.services.image_utils import load_image, scale_image_to_fit, image_to_bytes

logger = logging.getLogger(__name__)

# Render at 2x screen resolution for crisp preview
PREVIEW_SCALE = 2.0


class PreviewRenderer:
    """Renders a template to a QPixmap for GUI preview."""

    def __init__(self, layout_service: LabelLayoutService, qr_generator: QRGenerator):
        self.layout = layout_service
        self.qr = qr_generator

    def render(self, template: Template, page: int = 0) -> QPixmap:
        """Render one page of the template as a QPixmap."""
        geometry = AVERY_TEMPLATES[template.avery_template_id]
        positions = self.layout.compute_label_positions(geometry)
        per_page = geometry.labels_per_page

        w = int(geometry.page_width_pt * PREVIEW_SCALE)
        h = int(geometry.page_height_pt * PREVIEW_SCALE)

        image = QImage(w, h, QImage.Format.Format_ARGB32)
        image.fill(QColor(255, 255, 255))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(PREVIEW_SCALE, PREVIEW_SCALE)

        logo_pil = load_image(template.logo_path)

        # Draw label outlines and content
        label_start = page * per_page - template.start_offset
        for slot_idx, cell_rect in enumerate(positions):
            # Draw light border for each label slot
            painter.setPen(QPen(QColor(220, 220, 220), 0.5))
            painter.drawRect(QRectF(
                cell_rect.x, cell_rect.y, cell_rect.width, cell_rect.height
            ))

            label_idx = label_start + slot_idx
            if label_idx < 0 or label_idx >= len(template.labels):
                continue

            label = template.labels[label_idx]
            if label.is_empty():
                continue

            cell_layout = self.layout.compute_cell_layout(cell_rect)
            self._draw_label(painter, label, cell_layout, template.qr_base_url, logo_pil)

        painter.end()
        return QPixmap.fromImage(image)

    def _draw_label(
        self,
        painter: QPainter,
        label: LabelData,
        layout: CellLayout,
        qr_base_url: str,
        logo_pil,
    ) -> None:
        """Draw a single label's content."""
        # Part image
        part_pil = load_image(label.image_path)
        if part_pil:
            self._draw_pil_image(painter, part_pil, layout.image_rect)

        # Logo
        if logo_pil:
            self._draw_pil_image(painter, logo_pil, layout.logo_rect)

        # QR code
        if label.brennan_part_number:
            qr_pil = self.qr.generate(
                label.brennan_part_number,
                size_px=max(50, int(layout.qr_rect.width * 2)),
            )
            self._draw_pil_image(painter, qr_pil, layout.qr_rect)

        # Customer part number (top, left-aligned)
        if label.customer_part_number:
            fs = self._auto_font_size(label.customer_part_number, layout.customer_pn_rect.width, 8)
            painter.setFont(QFont("Helvetica", fs))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(
                QRectF(layout.customer_pn_rect.x, layout.customer_pn_rect.y,
                       layout.customer_pn_rect.width, layout.customer_pn_rect.height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label.customer_part_number,
            )

        # Brennan part number (bold, left-aligned)
        if label.brennan_part_number:
            fs = self._auto_font_size(label.brennan_part_number, layout.brennan_pn_rect.width, 14)
            font = QFont("Helvetica", fs)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(
                QRectF(layout.brennan_pn_rect.x, layout.brennan_pn_rect.y,
                       layout.brennan_pn_rect.width, layout.brennan_pn_rect.height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label.brennan_part_number,
            )

        # Description (left-aligned, small)
        if label.description:
            fs = self._auto_font_size(label.description, layout.description_rect.width, 6)
            painter.setFont(QFont("Helvetica", fs))
            painter.setPen(QColor(80, 80, 80))
            painter.drawText(
                QRectF(layout.description_rect.x, layout.description_rect.y,
                       layout.description_rect.width, layout.description_rect.height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label.description,
            )

    def _draw_pil_image(self, painter: QPainter, pil_img, rect) -> None:
        """Draw a PIL Image into the given rect area."""
        scaled = scale_image_to_fit(pil_img, int(rect.width * 2), int(rect.height * 2))
        data = image_to_bytes(scaled, "PNG")
        qimg = QImage()
        qimg.loadFromData(data)
        target = QRectF(rect.x, rect.y, rect.width, rect.height)
        painter.drawImage(target, qimg)

    def _auto_font_size(self, text: str, max_width: float, max_size: float = 12) -> float:
        if not text:
            return max_size
        needed = max_width / (len(text) * 0.6)
        return max(4.0, min(max_size, needed))
