"""Pure geometry engine for computing label positions on a sheet.

All coordinates are in points (72pt = 1 inch).
Origin is bottom-left of page (ReportLab convention).
"""
from dataclasses import dataclass
from typing import List

from src.models.avery_templates import AveryGeometry


@dataclass(frozen=True)
class Rect:
    """A rectangle defined by bottom-left corner + size, in points."""
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2


@dataclass(frozen=True)
class CellLayout:
    """Sub-regions within a single label cell."""
    image_rect: Rect      # part image (top-left)
    logo_rect: Rect       # logo (top-right)
    qr_rect: Rect         # QR code (bottom-left)
    customer_pn_rect: Rect  # customer part number text zone
    brennan_pn_rect: Rect   # Brennan part number text zone (large, bold)
    description_rect: Rect  # description text zone


class LabelLayoutService:
    """Computes label positions and cell internal layout."""

    def compute_label_positions(self, geometry: AveryGeometry) -> List[Rect]:
        """Return a list of Rects for every label slot on one page.

        Index 0 is top-left label, proceeding left-to-right, top-to-bottom.
        """
        positions = []
        lw = geometry.label_width_pt
        lh = geometry.label_height_pt
        left = geometry.left_margin_pt
        top_of_page = geometry.page_height_pt - geometry.top_margin_pt

        for row in range(geometry.rows):
            for col in range(geometry.columns):
                x = left + col * (lw + geometry.h_gap_pt)
                # y is bottom edge of label (ReportLab: origin at bottom-left)
                y = top_of_page - (row + 1) * lh - row * geometry.v_gap_pt
                positions.append(Rect(x, y, lw, lh))

        return positions

    def compute_cell_layout(self, cell: Rect) -> CellLayout:
        """Compute sub-regions within a label cell.

        Layout adapts proportionally to cell size.
        """
        w = cell.width
        h = cell.height
        pad = min(w, h) * 0.04  # 4% padding

        # Icon/image sizes scale with cell height
        icon_size = h * 0.35
        qr_size = h * 0.42

        # Part image: top-left
        image_rect = Rect(
            cell.x + pad,
            cell.top - pad - icon_size,
            icon_size,
            icon_size,
        )

        # Logo: top-right
        logo_rect = Rect(
            cell.right - pad - icon_size,
            cell.top - pad - icon_size,
            icon_size,
            icon_size,
        )

        # QR code: bottom-left
        qr_rect = Rect(
            cell.x + pad,
            cell.y + pad,
            qr_size,
            qr_size,
        )

        # Text zones fill remaining space
        text_left = cell.x + pad + icon_size + pad
        text_right = cell.right - pad - icon_size - pad
        text_width = text_right - text_left

        # Vertical split: customer_pn top third, brennan_pn middle, description bottom
        text_top = cell.top - pad
        text_bottom = cell.y + pad
        text_height = text_top - text_bottom

        row_h = text_height / 3.0

        customer_pn_rect = Rect(
            text_left, text_top - row_h,
            text_width, row_h,
        )
        brennan_pn_rect = Rect(
            text_left, text_top - 2 * row_h,
            text_width, row_h,
        )
        # Description spans wider — from QR right edge to cell right
        desc_left = cell.x + pad + qr_size + pad
        desc_width = cell.right - pad - desc_left
        description_rect = Rect(
            desc_left, cell.y + pad,
            desc_width, qr_size,
        )

        return CellLayout(
            image_rect=image_rect,
            logo_rect=logo_rect,
            qr_rect=qr_rect,
            customer_pn_rect=customer_pn_rect,
            brennan_pn_rect=brennan_pn_rect,
            description_rect=description_rect,
        )

    def compute_pages_needed(self, num_labels: int, geometry: AveryGeometry, start_offset: int = 0) -> int:
        """How many pages are needed for the given number of labels."""
        total_slots = num_labels + start_offset
        per_page = geometry.labels_per_page
        return max(1, (total_slots + per_page - 1) // per_page)
