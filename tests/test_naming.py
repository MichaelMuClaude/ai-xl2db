from ai_xl2db import naming


def test_snake_case_keeps_unicode_letters_and_drops_punctuation():
    assert naming.snake_case("  Total Sales (AUD) ") == "total_sales_aud"
    assert naming.snake_case("销售 额") == "销售_额"


def test_table_name_is_prefixed_when_it_starts_with_a_digit():
    assert naming.table_name("2026 Q1", set()) == "sheet_2026_q1"


def test_table_names_do_not_collide_with_reserved_or_each_other():
    taken = {"_sheets"}
    assert naming.table_name("Sheet One", taken) == "sheet_one"
    assert naming.table_name("sheet one", taken) == "sheet_one_2"
    assert naming.table_name("_sheets", taken) == "sheets"


def test_column_names_fill_blanks_and_dedupe():
    names = naming.column_names(["Region", None, "Region", "2nd", ""])
    assert names == ["region", "column_2", "region_2", "col_2nd", "column_5"]
