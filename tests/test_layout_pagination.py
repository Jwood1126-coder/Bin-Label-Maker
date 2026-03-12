"""Tests for layout engine pagination and position math."""
import pytest

from src.models.avery_templates import AVERY_TEMPLATES, AveryGeometry
from src.services.label_layout import LabelLayoutService


class TestLabelPositions:
    def setup_method(self):
        self.layout = LabelLayoutService()

    def test_5160_has_30_positions(self):
        geo = AVERY_TEMPLATES["5160"]
        positions = self.layout.compute_label_positions(geo)
        assert len(positions) == 30  # 3 cols x 10 rows

    def test_5163_has_10_positions(self):
        geo = AVERY_TEMPLATES["5163"]
        positions = self.layout.compute_label_positions(geo)
        assert len(positions) == 10  # 2 cols x 5 rows

    def test_5164_has_6_positions(self):
        geo = AVERY_TEMPLATES["5164"]
        positions = self.layout.compute_label_positions(geo)
        assert len(positions) == 6  # 2 cols x 3 rows

    def test_positions_within_page_bounds(self):
        for tid, geo in AVERY_TEMPLATES.items():
            positions = self.layout.compute_label_positions(geo)
            for pos in positions:
                assert pos.x >= 0, f"Template {tid}: x < 0"
                assert pos.y >= 0, f"Template {tid}: y < 0"
                assert pos.right <= geo.page_width_pt + 0.1, f"Template {tid}: right edge exceeds page"
                assert pos.top <= geo.page_height_pt + 0.1, f"Template {tid}: top edge exceeds page"

    def test_positions_no_overlap(self):
        for tid, geo in AVERY_TEMPLATES.items():
            positions = self.layout.compute_label_positions(geo)
            for i, a in enumerate(positions):
                for j, b in enumerate(positions):
                    if i >= j:
                        continue
                    # Check no horizontal overlap combined with vertical overlap
                    h_overlap = a.x < b.right and b.x < a.right
                    v_overlap = a.y < b.top and b.y < a.top
                    assert not (h_overlap and v_overlap), (
                        f"Template {tid}: positions {i} and {j} overlap"
                    )

    def test_top_left_is_first(self):
        """Position 0 should be the top-left label."""
        geo = AVERY_TEMPLATES["5160"]
        positions = self.layout.compute_label_positions(geo)
        first = positions[0]
        # Top-left means smallest x and largest y (ReportLab coords)
        for pos in positions[1:]:
            # First should be at or above all others
            assert first.top >= pos.y


class TestPagination:
    def setup_method(self):
        self.layout = LabelLayoutService()

    def test_zero_labels_one_page(self):
        geo = AVERY_TEMPLATES["5160"]
        assert self.layout.compute_pages_needed(0, geo) == 1

    def test_one_label_one_page(self):
        geo = AVERY_TEMPLATES["5160"]
        assert self.layout.compute_pages_needed(1, geo) == 1

    def test_exact_page_fill(self):
        geo = AVERY_TEMPLATES["5160"]  # 30 per page
        assert self.layout.compute_pages_needed(30, geo) == 1

    def test_one_over_needs_two_pages(self):
        geo = AVERY_TEMPLATES["5160"]  # 30 per page
        assert self.layout.compute_pages_needed(31, geo) == 2

    def test_start_offset(self):
        geo = AVERY_TEMPLATES["5160"]  # 30 per page
        # 25 labels + 5 offset = 30 slots = 1 page
        assert self.layout.compute_pages_needed(25, geo, start_offset=5) == 1
        # 26 labels + 5 offset = 31 slots = 2 pages
        assert self.layout.compute_pages_needed(26, geo, start_offset=5) == 2

    def test_large_offset(self):
        geo = AVERY_TEMPLATES["5160"]  # 30 per page
        # 1 label + 29 offset = 30 = 1 page
        assert self.layout.compute_pages_needed(1, geo, start_offset=29) == 1
        # 2 labels + 29 offset = 31 = 2 pages
        assert self.layout.compute_pages_needed(2, geo, start_offset=29) == 2


class TestCellLayout:
    def setup_method(self):
        self.layout = LabelLayoutService()

    def test_cell_layout_sub_regions_within_cell(self):
        geo = AVERY_TEMPLATES["5163"]
        positions = self.layout.compute_label_positions(geo)
        cell = positions[0]
        cl = self.layout.compute_cell_layout(cell)

        # All sub-regions should be within the cell bounds (with small tolerance)
        tol = 0.5
        for name, rect in [
            ("image", cl.image_rect),
            ("logo", cl.logo_rect),
            ("qr", cl.qr_rect),
            ("customer_pn", cl.customer_pn_rect),
            ("brennan_pn", cl.brennan_pn_rect),
            ("description", cl.description_rect),
        ]:
            assert rect.x >= cell.x - tol, f"{name} left edge outside cell"
            assert rect.y >= cell.y - tol, f"{name} bottom edge outside cell"
            assert rect.right <= cell.right + tol, f"{name} right edge outside cell"
            assert rect.top <= cell.top + tol, f"{name} top edge outside cell"
