"""QPixmap-based preview renderer for the GUI.

Renders the same layout as the PDF renderer but onto a QImage
for display in the preview panel.

NOTE: The layout engine uses ReportLab coordinates (origin at bottom-left,
y increases upward). Qt uses top-left origin (y increases downward).
All Rects from the layout engine must be flipped via _to_qt_rect().
"""
import logging

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QImage, QPainter, QColor, QFont, QPixmap, QPen, QFontMetricsF,
)

from src.models.avery_templates import AVERY_TEMPLATES
from src.models.template import Template
from src.models.label_data import LabelData
from src.services.label_layout import LabelLayoutService, CellLayout, Rect
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
        self._page_h = 0.0  # set per render call

    def _to_qt_rect(self, rect: Rect) -> QRectF:
        """Convert a ReportLab Rect (bottom-left origin) to a Qt QRectF (top-left origin)."""
        qt_y = self._page_h - rect.y - rect.height
        return QRectF(rect.x, qt_y, rect.width, rect.height)

    def render(self, template: Template, page: int = 0) -> QPixmap:
        """Render one page of the template as a QPixmap."""
        geometry = AVERY_TEMPLATES[template.avery_template_id]
        positions = self.layout.compute_label_positions(geometry)
        per_page = geometry.labels_per_page
        self._page_h = geometry.page_height_pt

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
            # Draw light border for each label slot (flip y for Qt)
            qt_rect = self._to_qt_rect(cell_rect)
            painter.setPen(QPen(QColor(220, 220, 220), 0.5))
            painter.drawRect(qt_rect)

            label_idx = label_start + slot_idx
            if label_idx < 0 or label_idx >= len(template.labels):
                continue

            label = template.labels[label_idx]
            if label.is_empty():
                continue

            cell_layout = self.layout.compute_cell_layout(cell_rect)
            self._draw_label(painter, label, template, cell_layout, logo_pil)

        painter.end()
        return QPixmap.fromImage(image)

    def _draw_label(
        self,
        painter: QPainter,
        label: LabelData,
        template: Template,
        layout: CellLayout,
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

        # QR code — uses template's qr_base_url
        if label.brennan_part_number:
            qr_pil = self.qr.generate(
                label.brennan_part_number,
                base_url=template.qr_base_url,
                size_px=max(50, int(layout.qr_rect.width * 2)),
            )
            self._draw_pil_image(painter, qr_pil, layout.qr_rect)

        # Customer part number (top, left-aligned)
        if label.customer_part_number:
            self._draw_clipped_text(
                painter, label.customer_part_number,
                QFont("Helvetica"), 8,
                layout.customer_pn_rect,
                QColor(0, 0, 0),
            )

        # Brennan part number (bold, left-aligned)
        if label.brennan_part_number:
            font = QFont("Helvetica")
            font.setBold(True)
            self._draw_clipped_text(
                painter, label.brennan_part_number,
                font, 14,
                layout.brennan_pn_rect,
                QColor(0, 0, 0),
            )

        # Description (left-aligned, small) — respects description mode
        display_desc = label.get_display_description(template.description_mode)
        if display_desc:
            self._draw_clipped_text(
                painter, display_desc,
                QFont("Helvetica"), 6,
                layout.description_rect,
                QColor(80, 80, 80),
            )

    def _draw_clipped_text(
        self,
        painter: QPainter,
        text: str,
        base_font: QFont,
        max_size: float,
        rect: Rect,
        color: QColor,
    ) -> None:
        """Draw text auto-sized to fit, clipped to rect boundary."""
        fs = self._auto_font_size(text, base_font, rect.width, max_size)
        font = QFont(base_font)
        font.setPointSizeF(fs)
        painter.setFont(font)
        painter.setPen(color)

        # Convert ReportLab rect to Qt rect and clip
        painter.save()
        target = self._to_qt_rect(rect)
        painter.setClipRect(target)
        painter.drawText(
            target,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
        )
        painter.restore()

    def _draw_pil_image(self, painter: QPainter, pil_img, rect: Rect) -> None:
        """Draw a PIL Image into the given rect area."""
        scaled = scale_image_to_fit(
            pil_img, int(rect.width * 2), int(rect.height * 2)
        )
        data = image_to_bytes(scaled, "PNG")
        qimg = QImage()
        qimg.loadFromData(data)
        target = self._to_qt_rect(rect)
        painter.drawImage(target, qimg)

    def _auto_font_size(
        self,
        text: str,
        base_font: QFont,
        max_width: float,
        max_size: float = 12,
    ) -> float:
        """Compute the largest font size that fits text within max_width.

        Uses QFontMetricsF for accurate glyph-based measurement.
        """
        if not text:
            return max_size
        size = max_size
        font = QFont(base_font)
        while size > 4.0:
            font.setPointSizeF(size)
            fm = QFontMetricsF(font)
            if fm.horizontalAdvance(text) <= max_width:
                return size
            size -= 0.5
        return 4.0
