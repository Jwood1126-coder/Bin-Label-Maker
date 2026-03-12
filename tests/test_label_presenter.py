"""Tests for LabelPresenter logic — dirty tracking, fill sheet, preflight."""
import pytest

from src.models.label_data import LabelData
from src.models.template import Template
from src.models.avery_templates import AVERY_TEMPLATES
from src.services.label_layout import LabelLayoutService
from src.services.qr_generator import QRGenerator
from src.services.pdf_renderer import PDFRenderer
from src.services.template_io import TemplateIO
from src.services.catsy_mock import MockCatsyService
from src.presenters.label_presenter import LabelPresenter


class FakeView:
    """Minimal view stub that records calls."""
    def __init__(self):
        self.calls = []

    def on_template_changed(self, template):
        self.calls.append(("template_changed", template))

    def on_labels_changed(self, labels, index):
        self.calls.append(("labels_changed", len(labels), index))

    def on_label_selected(self, label, index):
        self.calls.append(("label_selected", index))

    def on_preview_update_needed(self):
        self.calls.append(("preview_update",))

    def show_error(self, message):
        self.calls.append(("error", message))


def _make_presenter() -> tuple[LabelPresenter, FakeView]:
    layout = LabelLayoutService()
    qr = QRGenerator()
    pdf = PDFRenderer(layout, qr)
    io = TemplateIO()
    ds = MockCatsyService()
    p = LabelPresenter(pdf, io, ds)
    v = FakeView()
    p.set_view(v)
    return p, v


class TestDirtyTracking:
    def test_new_template_is_clean(self):
        p, v = _make_presenter()
        p.new_template()
        assert not p.is_dirty

    def test_adding_label_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        assert p.is_dirty

    def test_mark_clean_works(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        assert p.is_dirty
        p.mark_clean()
        assert not p.is_dirty

    def test_apply_template_is_clean(self):
        p, v = _make_presenter()
        p.add_label()
        assert p.is_dirty
        p.apply_template(Template())
        assert not p.is_dirty

    def test_setting_customer_name_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.set_customer_name("Test")
        assert p.is_dirty

    def test_setting_avery_template_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.set_avery_template("5163")
        assert p.is_dirty

    def test_update_label_field_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.mark_clean()
        p.update_label_field(0, "brennan_pn", "X-1")
        assert p.is_dirty

    def test_save_template_marks_clean(self, tmp_path):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        assert p.is_dirty
        path = str(tmp_path / "test.blm")
        result = p.save_template(path)
        assert result is True
        assert not p.is_dirty


class TestFillSheet:
    def test_fill_sheet_requires_selection(self):
        p, v = _make_presenter()
        p.new_template()
        msg = p.fill_sheet()
        assert "Select" in msg

    def test_fill_sheet_requires_non_empty_label(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()  # adds empty label
        p.select_label(0)
        msg = p.fill_sheet()
        assert "Select" in msg or "non-empty" in msg

    def test_fill_sheet_fills_correctly(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"  # 30 per page
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.select_label(0)
        msg = p.fill_sheet()
        assert "29" in msg  # should fill 29 more to make 30
        assert len(p.template.labels) == 30

    def test_fill_sheet_already_full(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"
        for _ in range(30):
            p.template.labels.append(LabelData(brennan_part_number="X-1"))
        p.select_label(0)
        msg = p.fill_sheet()
        assert "full" in msg.lower()
        assert len(p.template.labels) == 30

    def test_fill_sheet_respects_start_offset(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"  # 30 per page
        p.template.start_offset = 5
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.select_label(0)
        p.fill_sheet()
        # offset 5 + 1 label = 6 slots used, need 24 more
        assert len(p.template.labels) == 25


class TestPreflight:
    def test_preflight_empty_labels(self):
        p, v = _make_presenter()
        p.new_template()
        warnings = p.preflight_check()
        assert any("No labels" in w for w in warnings)

    def test_preflight_warns_empty_labels(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()  # empty
        p.add_label()
        p.template.labels[1].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        assert any("empty" in w.lower() for w in warnings)

    def test_preflight_warns_missing_brennan(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].customer_part_number = "CUST-1"  # non-empty but no brennan
        warnings = p.preflight_check()
        assert any("Brennan part number" in w for w in warnings)

    def test_preflight_clean_labels_no_critical_warnings(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        # Only informational warnings (partial page) expected, no critical issues
        assert not any("empty" in w.lower() and "label" in w.lower() for w in warnings)
        assert not any("No labels" in w for w in warnings)
        assert not any("Brennan part number" in w for w in warnings)


class TestLabelEditing:
    def test_update_description_field(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.update_label_field(0, "description", "Full text")
        assert p.template.labels[0].description == "Full text"

    def test_update_short_description_field(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.update_label_field(0, "short_description", "Short text")
        assert p.template.labels[0].short_description == "Short text"

    def test_replace_labels(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.add_label()
        assert len(p.template.labels) == 2

        new_labels = [LabelData(brennan_part_number="Y-1")]
        p.replace_labels(new_labels)
        assert len(p.template.labels) == 1
        assert p.template.labels[0].brennan_part_number == "Y-1"
        assert p.is_dirty

    def test_move_label_down(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "A"
        p.add_label()
        p.template.labels[1].brennan_part_number = "B"
        p.move_label(0, 1)
        assert p.template.labels[0].brennan_part_number == "B"
        assert p.template.labels[1].brennan_part_number == "A"
        assert p.is_dirty

    def test_move_label_up(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "A"
        p.add_label()
        p.template.labels[1].brennan_part_number = "B"
        p.move_label(1, -1)
        assert p.template.labels[0].brennan_part_number == "B"
        assert p.template.labels[1].brennan_part_number == "A"

    def test_move_label_out_of_bounds_noop(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "A"
        p.mark_clean()
        p.move_label(0, -1)  # can't move first item up
        assert p.template.labels[0].brennan_part_number == "A"
        assert not p.is_dirty  # no change happened


class TestPreflightDuplicates:
    def test_preflight_warns_duplicates(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.add_label()
        p.template.labels[1].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        assert any("Duplicate" in w for w in warnings)

    def test_preflight_no_duplicate_warning_for_unique(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.add_label()
        p.template.labels[1].brennan_part_number = "X-2"
        warnings = p.preflight_check()
        assert not any("Duplicate" in w for w in warnings)

    def test_preflight_warns_partial_page(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"  # 30 per page
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        assert any("empty slot" in w for w in warnings)
