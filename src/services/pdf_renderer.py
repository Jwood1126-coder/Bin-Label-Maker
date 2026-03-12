"""ReportLab-based PDF renderer for label sheets."""
import logging
from io import BytesIO
from typing import Optional

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from src.models.avery_templates import AVERY_TEMPLATES
from src.models.template import Template
from src.models.label_data import LabelData
from src.services.label_layout import LabelLayoutService, Rect, CellLayout
from src.services.qr_generator import QRGenerator
from src.services.image_utils import load_image, scale_image_to_fit

logger = logging.getLogger(__name__)


class PDFRenderer:
    """Renders a Template to a PDF file using ReportLab."""

    def __init__(self, layout_service: LabelLayoutService, qr_generator: QRGenerator):
        self.layout = layout_service
        self.qr = qr_generator

    def render(self, template: Template, output_path: str) -> None:
        """Generate a PDF file at output_path from the template."""
        geometry = AVERY_TEMPLATES[template.avery_template_id]
        positions = self.layout.compute_label_positions(geometry)
        per_page = geometry.labels_per_page

        c = Canvas(
            output_path,
            pagesize=(geometry.page_width_pt, geometry.page_height_pt),
        )

        logo_img = load_image(template.logo_path)

        label_index = 0
        slot_index = template.start_offset

        while label_index < len(template.labels):
            page_slot = slot_index % per_page

            if page_slot == 0 and slot_index > 0:
                c.showPage()

            if page_slot < len(positions):
                cell_rect = positions[page_slot]
                cell_layout = self.layout.compute_cell_layout(cell_rect)
                label = template.labels[label_index]
                self._draw_label(c, label, cell_layout, template, logo_img)
                label_index += 1

            slot_index += 1

        c.save()
        logger.info(
            "PDF saved to %s (%d labels)", output_path, len(template.labels)
        )

    def _draw_label(
        self,
        canvas: Canvas,
        label: LabelData,
        layout: CellLayout,
        template: Template,
        logo_img,
    ) -> None:
        """Draw a single label into its cell."""
        # Part image (top-left)
        self._draw_image(canvas, label.image_path, layout.image_rect)

        # Logo (top-right)
        if logo_img:
            self._draw_pil_image(canvas, logo_img, layout.logo_rect)

        # QR code (bottom-left) — uses template's qr_base_url
        if label.brennan_part_number:
            qr_img = self.qr.generate(
                label.brennan_part_number,
                base_url=template.qr_base_url,
                size_px=max(50, int(layout.qr_rect.width * 2)),
            )
            self._draw_pil_image(canvas, qr_img, layout.qr_rect)

        # Customer part number (top, left-aligned)
        if label.customer_part_number:
            self._draw_clipped_text(
                canvas, label.customer_part_number,
                "Helvetica", 8,
                layout.customer_pn_rect,
            )

        # Brennan part number (center, large bold, left-aligned)
        if label.brennan_part_number:
            self._draw_clipped_text(
                canvas, label.brennan_part_number,
                "Helvetica-Bold", 14,
                layout.brennan_pn_rect,
            )

        # Description (bottom, left-aligned, small) — respects description mode
        display_desc = label.get_display_description(template.description_mode)
        if display_desc:
            self._draw_clipped_text(
                canvas, display_desc,
                "Helvetica", 6,
                layout.description_rect,
            )

    def _draw_clipped_text(
        self,
        canvas: Canvas,
        text: str,
        font_name: str,
        max_size: float,
        rect: Rect,
    ) -> None:
        """Draw text that auto-sizes to fit and clips to the rect boundary."""
        font_size = self._auto_font_size(text, font_name, rect.width - 4, max_size)
        canvas.setFont(font_name, font_size)

        # Clip to the rect so text never bleeds into adjacent labels
        canvas.saveState()
        path = canvas.beginPath()
        path.rect(rect.x, rect.y, rect.width, rect.height)
        canvas.clipPath(path, stroke=0)
        canvas.drawString(
            rect.x + 2,
            rect.cy - font_size * 0.35,
            text,
        )
        canvas.restoreState()

    def _draw_image(
        self, canvas: Canvas, image_path: Optional[str], rect: Rect
    ) -> None:
        """Draw an image from a file path into the given rect."""
        img = load_image(image_path)
        if img:
            self._draw_pil_image(canvas, img, rect)

    def _draw_pil_image(self, canvas: Canvas, pil_img, rect: Rect) -> None:
        """Draw a PIL Image into the given rect, preserving aspect ratio."""
        scaled = scale_image_to_fit(
            pil_img, int(rect.width * 2), int(rect.height * 2)
        )
        buf = BytesIO()
        scaled.save(buf, format="PNG")
        buf.seek(0)
        reader = ImageReader(buf)

        # Center the image within the rect
        img_w, img_h = scaled.size
        display_w = min(rect.width, img_w / 2)
        display_h = min(rect.height, img_h / 2)
        ratio = min(rect.width / display_w, rect.height / display_h)
        draw_w = display_w * ratio
        draw_h = display_h * ratio
        draw_x = rect.x + (rect.width - draw_w) / 2
        draw_y = rect.y + (rect.height - draw_h) / 2

        canvas.drawImage(reader, draw_x, draw_y, draw_w, draw_h, mask="auto")

    def _auto_font_size(
        self,
        text: str,
        font_name: str,
        max_width: float,
        max_size: float = 12,
    ) -> float:
        """Compute the largest font size that fits text within max_width.

        Uses ReportLab's stringWidth for accurate glyph-based measurement.
        """
        if not text:
            return max_size
        size = max_size
        while size > 4.0:
            if stringWidth(text, font_name, size) <= max_width:
                return size
            size -= 0.5
        return 4.0
