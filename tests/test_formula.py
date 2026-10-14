import pytest

from ai_xl2db import formula
from ai_xl2db.formula import UnsupportedFormula

COLUMNS = ["region", "units", "price", "date", "region_2"]


@pytest.mark.parametrize(
    "excel, python",
    [
        ("=B4+1", "(cell(sheet, 'units', 4) + 1)"),
        ("=SUM(B4:B7)", "SUM(rng(sheet, 'units', 4, 7))"),
        ("=C4*2", "(cell(sheet, 'price', 4) * 2)"),
        ("=-2^2", "((-2) ** 2)"),  # Excel: unary minus binds before ^, so -2^2 is 4
        ("=1+2*3", "(1 + (2 * 3))"),
        ("=A1&\"x\"", "concat(cell(sheet, 'region', 1), 'x')"),
        ("=B4=5", "(cell(sheet, 'units', 4) == 5)"),
        ("=B4<>5", "(cell(sheet, 'units', 4) != 5)"),
        ("=IF(B4>5,\"big\",\"small\")", "IF((cell(sheet, 'units', 4) > 5), 'big', 'small')"),
        ("=ROUND(C4,1)", "ROUND(cell(sheet, 'price', 4), 1)"),
        ("=$B$4", "cell(sheet, 'units', 4)"),
    ],
)
def test_supported_formulas_translate(excel, python):
    expression, _ = formula.translate(excel, COLUMNS)
    assert expression == python


@pytest.mark.parametrize(
    "excel, reason",
    [
        ("=VLOOKUP(A4,B:C,2,FALSE)", "not supported"),
        ("=Other!B4", "other sheets"),
        ("=SUM(A4:B5)", "more than one column"),
        ("=Z99", "outside the table"),
        ("=B4 B5", "unexpected"),
    ],
)
def test_unsupported_formulas_say_why(excel, reason):
    with pytest.raises(UnsupportedFormula, match=reason):
        formula.translate(excel, COLUMNS)


def test_script_imports_only_the_names_it_uses():
    script = formula.script_for("=SUM(B4:B7)", COLUMNS, "units", 8, "Sales 2026")
    assert "from ai_xl2db.runtime import SUM, rng" in script
    assert "def compute(sheet):" in script
    assert "return SUM(rng(sheet, 'units', 4, 7))" in script
    compile(script, "<formula>", "exec")  # the generated script is valid Python
