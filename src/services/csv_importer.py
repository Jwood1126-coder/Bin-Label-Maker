"""Import labels from CSV or Excel files."""
import csv
import logging
from typing import List

from src.models.label_data import LabelData

logger = logging.getLogger(__name__)

# Column name aliases (case-insensitive matching)
_BRENNAN_ALIASES = {"brennan_part_number", "brennan_pn", "brennan part number", "brennan part #", "brennan p/n", "brennan", "part number", "part_number", "part #", "part#", "pn"}
_CUSTOMER_ALIASES = {"customer_part_number", "customer_pn", "customer part number", "customer part #", "customer p/n", "customer", "customer #", "customer#", "cust_pn", "cust pn"}
_DESCRIPTION_ALIASES = {"description", "desc", "part description", "item description", "name"}


def _find_column(headers: List[str], aliases: set) -> int:
    """Find the column index matching any of the aliases. Returns -1 if not found."""
    for i, h in enumerate(headers):
        if h.strip().lower() in aliases:
            return i
    return -1


def import_labels_from_csv(file_path: str) -> List[LabelData]:
    """Import labels from a CSV file."""
    labels = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            return []

        brennan_col = _find_column(headers, _BRENNAN_ALIASES)
        customer_col = _find_column(headers, _CUSTOMER_ALIASES)
        desc_col = _find_column(headers, _DESCRIPTION_ALIASES)

        if brennan_col == -1 and customer_col == -1:
            # Fallback: assume first 3 columns are brennan, customer, description
            brennan_col, customer_col, desc_col = 0, 1, 2 if len(headers) > 2 else (0, 1, -1)

        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            brennan = row[brennan_col].strip() if brennan_col >= 0 and brennan_col < len(row) else ""
            customer = row[customer_col].strip() if customer_col >= 0 and customer_col < len(row) else ""
            desc = row[desc_col].strip() if desc_col >= 0 and desc_col < len(row) else ""
            if brennan or customer:
                labels.append(LabelData(
                    brennan_part_number=brennan,
                    customer_part_number=customer,
                    description=desc,
                ))

    logger.info("Imported %d labels from CSV: %s", len(labels), file_path)
    return labels


def import_labels_from_excel(file_path: str) -> List[LabelData]:
    """Import labels from an Excel (.xlsx/.xls) file."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl is required for Excel import. Install it with: pip install openpyxl"
        )

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    labels = []

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(cell or "").strip() for cell in rows[0]]
    brennan_col = _find_column(headers, _BRENNAN_ALIASES)
    customer_col = _find_column(headers, _CUSTOMER_ALIASES)
    desc_col = _find_column(headers, _DESCRIPTION_ALIASES)

    if brennan_col == -1 and customer_col == -1:
        brennan_col, customer_col = 0, 1
        desc_col = 2 if len(headers) > 2 else -1

    for row in rows[1:]:
        if not any(str(cell or "").strip() for cell in row):
            continue
        brennan = str(row[brennan_col] or "").strip() if brennan_col >= 0 and brennan_col < len(row) else ""
        customer = str(row[customer_col] or "").strip() if customer_col >= 0 and customer_col < len(row) else ""
        desc = str(row[desc_col] or "").strip() if desc_col >= 0 and desc_col < len(row) else ""
        if brennan or customer:
            labels.append(LabelData(
                brennan_part_number=brennan,
                customer_part_number=customer,
                description=desc,
            ))

    wb.close()
    logger.info("Imported %d labels from Excel: %s", len(labels), file_path)
    return labels


def import_labels_from_file(file_path: str) -> List[LabelData]:
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
