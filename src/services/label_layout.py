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
    """Sub-regions within a single label cell.

    Layout matches the reference image:
    +----------------------------------------------+
    | [IMG]  Customer Part #           [LOGO]      |
    | [IMG]  BRENNAN PART # (bold)                 |
    | [QR]   Description (small)                   |
    +----------------------------------------------+
    """
    image_rect: Rect      # part image (left column, top half)
    logo_rect: Rect       # logo (top-right corner)
    qr_rect: Rect         # QR code (left column, bottom half)
    customer_pn_rect: Rect  # customer part number text zone (top row)
    brennan_pn_rect: Rect   # Brennan part number text zone (middle, large bold)
    description_rect: Rect  # description text zone (bottom row)


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

        Layout matches the reference image:
        - Left column (~28%): part image (top) + QR code (bottom)
        - Center area: customer# (top) + Brennan# (middle, large bold) + description (bottom)
        - Logo: small, top-right corner
        """
        w = cell.width
        h = cell.height
        pad = min(w, h) * 0.03

        # Left column for image/QR takes ~28% of width
        left_col_w = w * 0.28
        # Logo is a small square in the top-right corner
        logo_size = h * 0.28

        # Part image: left column, top portion
        img_size = min(left_col_w - 2 * pad, h * 0.52)
        image_rect = Rect(
            cell.x + pad,
            cell.top - pad - img_size,
            img_size,
            img_size,
        )

        # QR code: left column, bottom portion
        qr_size = min(left_col_w - 2 * pad, h * 0.40)
        qr_rect = Rect(
            cell.x + pad,
            cell.y + pad,
            qr_size,
            qr_size,
        )

        # Logo: top-right corner
        logo_rect = Rect(
            cell.right - pad - logo_size,
            cell.top - pad - logo_size,
            logo_size,
            logo_size,
        )

        # Text area: right of left column, left of logo
        text_left = cell.x + left_col_w
        text_right = cell.right - pad - logo_size - pad
        text_width = max(text_right - text_left, w * 0.3)

        # Vertical text zones
        text_top = cell.top - pad
        text_h = text_top - (cell.y + pad)

        # Customer P/N: top 25%
        cust_h = text_h * 0.25
        customer_pn_rect = Rect(
            text_left, text_top - cust_h,
            text_width, cust_h,
        )

        # Brennan P/N: middle 45% (the main bold number)
        brennan_h = text_h * 0.45
        brennan_pn_rect = Rect(
            text_left, text_top - cust_h - brennan_h,
            text_width, brennan_h,
        )

        # Description: bottom 30%
        desc_h = text_h * 0.30
        description_rect = Rect(
            text_left, cell.y + pad,
            text_width, desc_h,
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
