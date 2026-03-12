"""Tests for save/load roundtrip fidelity."""
import json
import os
import pytest

from src.models.template import Template, DESC_MODE_SHORT
from src.models.label_data import LabelData
from src.services.template_io import TemplateIO


class TestTemplateRoundtrip:
    def test_empty_template_roundtrip(self, tmp_path):
        io = TemplateIO()
        original = Template()
        path = str(tmp_path / "test.blm")
        io.save(original, path)
        loaded = io.load(path)

        assert loaded.customer_name == original.customer_name
        assert loaded.avery_template_id == original.avery_template_id
        assert loaded.qr_base_url == original.qr_base_url
        assert loaded.xref_key == original.xref_key
        assert loaded.description_mode == original.description_mode
        assert loaded.start_offset == original.start_offset
        assert loaded.labels == []

    def test_full_template_roundtrip(self, tmp_path):
        io = TemplateIO()
        original = Template(
            customer_name="ACME Corp",
            avery_template_id="5163",
            qr_base_url="https://example.com/",
            xref_key="parker_part_number",
            description_mode=DESC_MODE_SHORT,
            start_offset=3,
            labels=[
                LabelData(
                    brennan_part_number="2404-04-02",
                    customer_part_number="CUST-001",
                    description="Full description text",
                    short_description="Short desc",
                ),
                LabelData(
                    brennan_part_number="2404-06-04",
                    customer_part_number="CUST-002",
                    description="Another full desc",
                    short_description="Another short",
                ),
            ],
        )
        path = str(tmp_path / "test.blm")
        io.save(original, path)
        loaded = io.load(path)

        assert loaded.customer_name == "ACME Corp"
        assert loaded.avery_template_id == "5163"
        assert loaded.qr_base_url == "https://example.com/"
        assert loaded.xref_key == "parker_part_number"
        assert loaded.description_mode == DESC_MODE_SHORT
        assert loaded.start_offset == 3
        assert len(loaded.labels) == 2
        assert loaded.labels[0].brennan_part_number == "2404-04-02"
        assert loaded.labels[0].customer_part_number == "CUST-001"
        assert loaded.labels[0].description == "Full description text"
        assert loaded.labels[0].short_description == "Short desc"
        assert loaded.labels[1].brennan_part_number == "2404-06-04"

    def test_forward_compatible_loading(self, tmp_path):
        """Unknown fields in JSON should be tolerated."""
        path = str(tmp_path / "future.blm")
        data = {
            "customer_name": "Test",
            "avery_template_id": "5160",
            "future_field": "some_value",
            "labels": [
                {
                    "brennan_part_number": "X-1",
                    "customer_part_number": "",
                    "description": "test",
                    "short_description": "",
                    "new_future_field": 42,
                }
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f)

        io = TemplateIO()
        loaded = io.load(path)
        assert loaded.customer_name == "Test"
        assert len(loaded.labels) == 1
        assert loaded.labels[0].brennan_part_number == "X-1"

    def test_missing_fields_get_defaults(self, tmp_path):
        """Minimal JSON should load with defaults for missing fields."""
        path = str(tmp_path / "minimal.blm")
        data = {"labels": [{"brennan_part_number": "X-1"}]}
        with open(path, "w") as f:
            json.dump(data, f)

        io = TemplateIO()
        loaded = io.load(path)
        assert loaded.customer_name == ""
        assert loaded.avery_template_id == "5160"
        assert loaded.description_mode == "full"
        assert loaded.start_offset == 0
        assert len(loaded.labels) == 1
