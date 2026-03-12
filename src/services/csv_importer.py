"""Import labels from CSV, Excel, or clipboard text."""
import csv
import io
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.models.label_data import LabelData

logger = logging.getLogger(__name__)

# Column name aliases (case-insensitive matching)
_BRENNAN_ALIASES = {
    "brennan_part_number", "brennan_pn", "brennan part number", "brennan part #",
    "brennan p/n", "brennan", "part number", "part_number", "part #", "part#", "pn",
    "brennan #", "brennan#", "bpn", "part no", "part no.", "part_no",
}
_CUSTOMER_ALIASES = {
    "customer_part_number", "customer_pn", "customer part number", "customer part #",
    "customer p/n", "customer", "customer #", "customer#", "cust_pn", "cust pn",
    "cust part number", "cust part #", "cust p/n", "cust #", "cust#",
    "customer number", "customer_number", "cust number", "cust_number",
    "customer no", "customer no.", "cust no", "cust no.",
    "cross reference", "cross_reference", "cross ref", "cross_ref", "xref",
    "their part number", "their p/n", "their pn", "their #",
    "oem", "oem part number", "oem pn", "oem #", "oem p/n",
    "mfg part number", "mfg pn", "mfg #", "mfg p/n",
    "manufacturer part number", "manufacturer pn",
}
_DESCRIPTION_ALIASES = {"description", "desc", "part description", "item description", "name"}
_SHORT_DESC_ALIASES = {"short_description", "short_desc", "short description", "short desc", "compact description", "compact desc"}


@dataclass
class ImportResult:
    """Result of an import operation with metadata for user feedback."""
    labels: List[LabelData] = field(default_factory=list)
    total_rows: int = 0
    skipped_rows: int = 0
    column_mapping: dict = field(default_factory=dict)  # field_name -> column_header

    @property
    def imported_count(self) -> int:
        return len(self.labels)

    def summary(self) -> str:
        parts = [f"{self.imported_count} label(s) imported"]
        if self.skipped_rows:
            parts.append(f"{self.skipped_rows} empty row(s) skipped")
        if self.column_mapping:
            mapped = ", ".join(f"{k} \u2190 \"{v}\"" for k, v in self.column_mapping.items())
            parts.append(f"Columns: {mapped}")
        return "\n".join(parts)


def _find_column(headers: List[str], aliases: set) -> int:
    """Find the column index matching any of the aliases. Returns -1 if not found."""
    for i, h in enumerate(headers):
        if h.strip().lower() in aliases:
            return i
    return -1


def _resolve_columns(headers: List[str]) -> tuple:
    """Resolve column indices for all fields. Returns (brennan, customer, desc, short_desc, mapping)."""
    brennan_col = _find_column(headers, _BRENNAN_ALIASES)
    customer_col = _find_column(headers, _CUSTOMER_ALIASES)
    desc_col = _find_column(headers, _DESCRIPTION_ALIASES)
    short_desc_col = _find_column(headers, _SHORT_DESC_ALIASES)

    mapping = {}

    if brennan_col == -1 and customer_col == -1:
        # Fallback: assume first columns are brennan, customer, description
        brennan_col = 0
        customer_col = 1 if len(headers) > 1 else -1
        desc_col = 2 if len(headers) > 2 else -1
        if brennan_col >= 0:
            mapping["Brennan P/N"] = headers[brennan_col] if brennan_col < len(headers) else f"Column {brennan_col + 1}"
        if customer_col >= 0:
            mapping["Customer P/N"] = headers[customer_col] if customer_col < len(headers) else f"Column {customer_col + 1}"
        if desc_col >= 0:
            mapping["Description"] = headers[desc_col] if desc_col < len(headers) else f"Column {desc_col + 1}"
    else:
        if brennan_col >= 0:
            mapping["Brennan P/N"] = headers[brennan_col]
        if customer_col >= 0:
            mapping["Customer P/N"] = headers[customer_col]
        if desc_col >= 0:
            mapping["Description"] = headers[desc_col]
        if short_desc_col >= 0:
            mapping["Short Desc"] = headers[short_desc_col]

    return brennan_col, customer_col, desc_col, short_desc_col, mapping


def _safe_get(row, col, is_str=True):
    """Safely get a cell value, returning empty string if out of bounds."""
    if col < 0 or col >= len(row):
        return ""
    val = row[col]
    if is_str:
        return str(val or "").strip() if val is not None else ""
    return val


def import_labels_from_csv(file_path: str) -> ImportResult:
    """Import labels from a CSV file. Returns ImportResult with metadata."""
    result = ImportResult()
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            return result

        brennan_col, customer_col, desc_col, short_desc_col, mapping = _resolve_columns(headers)
        result.column_mapping = mapping

        for row in reader:
            result.total_rows += 1
            if not any(cell.strip() for cell in row):
                result.skipped_rows += 1
                continue
            brennan = _safe_get(row, brennan_col)
            customer = _safe_get(row, customer_col)
            desc = _safe_get(row, desc_col)
            short_desc = _safe_get(row, short_desc_col)
            if brennan or customer:
                result.labels.append(LabelData(
                    brennan_part_number=brennan,
                    customer_part_number=customer,
                    description=desc,
                    short_description=short_desc,
                ))
            else:
                result.skipped_rows += 1

    logger.info("Imported %d labels from CSV: %s", result.imported_count, file_path)
    return result


def import_labels_from_excel(file_path: str) -> ImportResult:
    """Import labels from an Excel (.xlsx/.xls) file. Returns ImportResult with metadata."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl is required for Excel import. Install it with: pip install openpyxl"
        )

    result = ImportResult()
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return result

    headers = [str(cell or "").strip() for cell in rows[0]]
    brennan_col, customer_col, desc_col, short_desc_col, mapping = _resolve_columns(headers)
    result.column_mapping = mapping

    for row in rows[1:]:
        result.total_rows += 1
        if not any(str(cell or "").strip() for cell in row):
            result.skipped_rows += 1
            continue
        brennan = str(row[brennan_col] or "").strip() if brennan_col >= 0 and brennan_col < len(row) else ""
        customer = str(row[customer_col] or "").strip() if customer_col >= 0 and customer_col < len(row) else ""
        desc = str(row[desc_col] or "").strip() if desc_col >= 0 and desc_col < len(row) else ""
        short_desc = str(row[short_desc_col] or "").strip() if short_desc_col >= 0 and short_desc_col < len(row) else ""
        if brennan or customer:
            result.labels.append(LabelData(
                brennan_part_number=brennan,
                customer_part_number=customer,
                description=desc,
                short_description=short_desc,
            ))
        else:
            result.skipped_rows += 1

    wb.close()
    logger.info("Imported %d labels from Excel: %s", result.imported_count, file_path)
    return result


def import_labels_from_file(file_path: str) -> ImportResult:
    """Auto-detect file type and import labels."""
    lower = file_path.lower()
    if lower.endswith(".csv"):
        return import_labels_from_csv(file_path)
    elif lower.endswith((".xlsx", ".xls")):
        return import_labels_from_excel(file_path)
    else:
        # Try CSV first, fall back to Excel
        try:
            return import_labels_from_csv(file_path)
        except Exception:
            return import_labels_from_excel(file_path)


def parse_clipboard_text(text: str) -> ImportResult:
    """Parse tab-separated or CSV text from clipboard into labels.

    Handles:
    - Tab-separated rows (typical Excel paste)
    - CSV-formatted rows
    - Single column of part numbers
    """
    result = ImportResult()
    if not text or not text.strip():
        return result

    lines = text.strip().splitlines()
    if not lines:
        return result

    # Detect delimiter: if tabs present, use tab; otherwise try CSV
    if "\t" in lines[0]:
        rows = [line.split("\t") for line in lines]
    else:
        try:
            reader = csv.reader(io.StringIO(text.strip()))
            rows = list(reader)
        except csv.Error:
            # Treat each line as a single part number
            rows = [[line.strip()] for line in lines]

    if not rows:
        return result

    # Check if first row looks like a header
    headers = [cell.strip() for cell in rows[0]]
    brennan_col, customer_col, desc_col, short_desc_col, mapping = _resolve_columns(headers)

    # If recognized headers were found, skip the header row
    has_header = (_find_column(headers, _BRENNAN_ALIASES) >= 0
                  or _find_column(headers, _CUSTOMER_ALIASES) >= 0
                  or _find_column(headers, _DESCRIPTION_ALIASES) >= 0)
    data_rows = rows[1:] if has_header else rows
    if has_header:
        result.column_mapping = mapping
    else:
        # Re-resolve without header recognition
        brennan_col = 0
        customer_col = 1 if len(headers) > 1 else -1
        desc_col = 2 if len(headers) > 2 else -1
        short_desc_col = -1

    for row in data_rows:
        result.total_rows += 1
        if not any(cell.strip() for cell in row):
            result.skipped_rows += 1
            continue
        brennan = _safe_get(row, brennan_col)
        customer = _safe_get(row, customer_col)
        desc = _safe_get(row, desc_col)
        short_desc = _safe_get(row, short_desc_col)
        if brennan or customer:
            result.labels.append(LabelData(
                brennan_part_number=brennan,
                customer_part_number=customer,
                description=desc,
                short_description=short_desc,
            ))
        else:
            result.skipped_rows += 1

    logger.info("Parsed %d labels from clipboard text", result.imported_count)
    return result
