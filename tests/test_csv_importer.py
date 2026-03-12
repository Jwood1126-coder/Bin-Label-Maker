"""Tests for CSV/Excel import edge cases."""
import csv

from src.services.csv_importer import (
    import_labels_from_csv, import_labels_from_file,
    parse_clipboard_text,
)


def _write_csv(rows: list[list[str]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


class TestCSVImport:
    def test_standard_3_column_with_headers(self, tmp_path):
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["brennan_part_number", "customer_part_number", "description"],
            ["2404-04-02", "CUST-001", "Steel connector"],
            ["2404-06-04", "CUST-002", "Brass fitting"],
        ], path)
        result = import_labels_from_csv(path)
        assert len(result.labels) == 2
        assert result.labels[0].brennan_part_number == "2404-04-02"
        assert result.labels[0].customer_part_number == "CUST-001"
        assert result.labels[0].description == "Steel connector"

    def test_2_column_file_fallback(self, tmp_path):
        """2-column file with no recognized headers should use columns as brennan, customer."""
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["col_a", "col_b"],
            ["2404-04-02", "CUST-001"],
            ["2404-06-04", "CUST-002"],
        ], path)
        result = import_labels_from_csv(path)
        assert len(result.labels) == 2
        assert result.labels[0].brennan_part_number == "2404-04-02"
        assert result.labels[0].customer_part_number == "CUST-001"
        assert result.labels[0].description == ""  # no desc column

    def test_1_column_file_fallback(self, tmp_path):
        """1-column file should put values in brennan_part_number."""
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["stuff"],
            ["2404-04-02"],
            ["2404-06-04"],
        ], path)
        result = import_labels_from_csv(path)
        assert len(result.labels) == 2
        assert result.labels[0].brennan_part_number == "2404-04-02"
        assert result.labels[0].customer_part_number == ""

    def test_alias_matching(self, tmp_path):
        """Various column name aliases should be recognized."""
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["Brennan Part #", "Customer P/N", "Desc"],
            ["2404-04-02", "CUST-001", "Fitting"],
        ], path)
        result = import_labels_from_csv(path)
        assert len(result.labels) == 1
        assert result.labels[0].brennan_part_number == "2404-04-02"
        assert result.labels[0].customer_part_number == "CUST-001"
        assert result.labels[0].description == "Fitting"

    def test_empty_rows_skipped(self, tmp_path):
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["brennan_part_number", "customer_part_number", "description"],
            ["2404-04-02", "CUST-001", "Steel"],
            ["", "", ""],
            ["", "", ""],
            ["2404-06-04", "CUST-002", "Brass"],
        ], path)
        result = import_labels_from_csv(path)
        assert len(result.labels) == 2
        assert result.skipped_rows == 2

    def test_empty_file_returns_empty(self, tmp_path):
        path = str(tmp_path / "test.csv")
        _write_csv([], path)
        result = import_labels_from_csv(path)
        assert result.labels == []

    def test_header_only_returns_empty(self, tmp_path):
        path = str(tmp_path / "test.csv")
        _write_csv([["brennan_part_number", "customer_part_number"]], path)
        result = import_labels_from_csv(path)
        assert result.labels == []

    def test_special_characters_preserved(self, tmp_path):
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["brennan_part_number", "description"],
            ['2404-04-02', '1/4" Male JIC x 1/8" Male NPTF'],
        ], path)
        result = import_labels_from_csv(path)
        assert len(result.labels) == 1
        assert '1/4"' in result.labels[0].description

    def test_file_type_detection(self, tmp_path):
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["part_number", "customer_part_number"],
            ["2404-04-02", "CUST-001"],
        ], path)
        result = import_labels_from_file(path)
        assert len(result.labels) == 1

    def test_short_description_column(self, tmp_path):
        """Short description column should be mapped when present."""
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["brennan_part_number", "description", "short_description"],
            ["2404-04-02", "Full description text", "04MJ x 02MP"],
        ], path)
        result = import_labels_from_csv(path)
        assert len(result.labels) == 1
        assert result.labels[0].description == "Full description text"
        assert result.labels[0].short_description == "04MJ x 02MP"

    def test_short_desc_alias(self, tmp_path):
        """Short desc alias should be recognized."""
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["brennan_part_number", "description", "short desc"],
            ["2404-04-02", "Full desc", "Short"],
        ], path)
        result = import_labels_from_csv(path)
        assert result.labels[0].short_description == "Short"

    def test_import_result_summary(self, tmp_path):
        """ImportResult should provide a human-readable summary."""
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["brennan_part_number", "customer_part_number"],
            ["2404-04-02", "CUST-001"],
            ["", ""],
            ["2404-06-04", "CUST-002"],
        ], path)
        result = import_labels_from_csv(path)
        summary = result.summary()
        assert "2 label(s) imported" in summary
        assert "1 empty row(s) skipped" in summary

    def test_column_mapping_reported(self, tmp_path):
        """Column mapping should be reported in results."""
        path = str(tmp_path / "test.csv")
        _write_csv([
            ["Brennan Part #", "Customer P/N", "Desc"],
            ["2404-04-02", "CUST-001", "Fitting"],
        ], path)
        result = import_labels_from_csv(path)
        assert "Brennan P/N" in result.column_mapping
        assert result.column_mapping["Brennan P/N"] == "Brennan Part #"


class TestClipboardPaste:
    def test_tab_separated_with_header(self):
        text = "brennan_part_number\tcustomer_part_number\tdescription\n2404-04-02\tCUST-001\tSteel connector\n2404-06-04\tCUST-002\tBrass fitting"
        result = parse_clipboard_text(text)
        assert len(result.labels) == 2
        assert result.labels[0].brennan_part_number == "2404-04-02"
        assert result.labels[0].customer_part_number == "CUST-001"
        assert result.labels[0].description == "Steel connector"

    def test_tab_separated_no_header(self):
        text = "2404-04-02\tCUST-001\n2404-06-04\tCUST-002"
        result = parse_clipboard_text(text)
        assert len(result.labels) == 2
        assert result.labels[0].brennan_part_number == "2404-04-02"
        assert result.labels[0].customer_part_number == "CUST-001"

    def test_single_column_paste(self):
        text = "2404-04-02\n2404-06-04\n2404-08-06"
        result = parse_clipboard_text(text)
        assert len(result.labels) == 3
        assert result.labels[0].brennan_part_number == "2404-04-02"

    def test_csv_format_paste(self):
        text = "brennan_part_number,customer_part_number\n2404-04-02,CUST-001"
        result = parse_clipboard_text(text)
        assert len(result.labels) == 1
        assert result.labels[0].brennan_part_number == "2404-04-02"

    def test_empty_clipboard(self):
        result = parse_clipboard_text("")
        assert result.labels == []

    def test_whitespace_only(self):
        result = parse_clipboard_text("   \n  \n  ")
        assert result.labels == []

    def test_empty_rows_skipped(self):
        text = "2404-04-02\tCUST-001\n\t\n2404-06-04\tCUST-002"
        result = parse_clipboard_text(text)
        assert len(result.labels) == 2
        assert result.skipped_rows == 1

    def test_short_description_in_paste(self):
        text = "brennan_part_number\tdescription\tshort_description\n2404-04-02\tFull desc\tShort"
        result = parse_clipboard_text(text)
        assert len(result.labels) == 1
        assert result.labels[0].short_description == "Short"
