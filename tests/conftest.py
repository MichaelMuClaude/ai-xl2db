import datetime
from pathlib import Path

import pytest


@pytest.fixture
def messy_xlsx(tmp_path: Path) -> Path:
    """A workbook with a title row, a blank row, a formula, dates, mixed values, and an empty sheet."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales 2026"
    ws["A1"] = "Quarterly sales report"  # title row: one filled cell, should be skipped
    ws.append([])  # blank row
    ws.append(["Region", "Units", "Price", "Date", "Region"])  # duplicate header name
    ws.append(["North", 10, 2.5, datetime.date(2026, 1, 5), "x"])
    ws.append(["South", 20, 3.0, datetime.date(2026, 2, 9), "y"])
    ws.append([None, None, None, None, None])  # blank data row
    ws.append(["East", 5, "n/a", None, "z"])  # mixed type in Price
    ws.append(["Total", "=SUM(B4:B6)", None, None, None])  # formula

    empty = wb.create_sheet("Empty")
    empty["A1"] = None

    ws2 = wb.create_sheet("2nd sheet")
    ws2.append(["Name", "Note"])
    ws2.append(["Zhang", "中文备注"])

    path = tmp_path / "messy.xlsx"
    wb.save(path)
    return path
