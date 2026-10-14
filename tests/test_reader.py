from ai_xl2db import reader


def test_title_rows_and_blank_rows_are_skipped(messy_xlsx):
    sheets = {s.title: s for s in reader.read_xlsx(messy_xlsx)}
    sales = sheets["Sales 2026"]
    assert sales.header == ["Region", "Units", "Price", "Date", "Region"]
    # blank data row is dropped: North, South, East, Total
    assert [row[0] for row in sales.rows] == ["North", "South", "East", "Total"]


def test_empty_sheet_is_not_returned(messy_xlsx):
    titles = [s.title for s in reader.read_xlsx(messy_xlsx)]
    assert "Empty" not in titles
    assert "2nd sheet" in titles


def test_formula_text_is_kept_by_position(messy_xlsx):
    sales = next(s for s in reader.read_xlsx(messy_xlsx) if s.title == "Sales 2026")
    # the Total row is the 4th data row (index 3); its Units cell (spreadsheet row 8) holds the SUM formula
    assert sales.formulas[(3, 1)][0] == "=SUM(B4:B6)"
    assert sales.row_numbers == [4, 5, 7, 8]  # blank row 6 is not counted


def test_csv_numbers_and_leading_zeros(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("code,count\n007,3\n1.5,4\n", encoding="utf-8")
    sheet = reader.read_csv(path)[0]
    assert sheet.rows[0] == ["007", 3]  # leading zero kept as text
    assert sheet.rows[1] == [1.5, 4]


def test_csv_with_bom_and_gb18030(tmp_path):
    path = tmp_path / "zh.csv"
    path.write_bytes("名称,数量\n苹果,3\n".encode("gb18030"))
    sheet = reader.read_csv(path)[0]
    assert sheet.header == ["名称", "数量"]
    assert sheet.rows == [["苹果", 3]]


def test_unsupported_extension_raises(tmp_path):
    import pytest

    path = tmp_path / "notes.txt"
    path.write_text("x")
    with pytest.raises(ValueError):
        reader.read_spreadsheet(path)
