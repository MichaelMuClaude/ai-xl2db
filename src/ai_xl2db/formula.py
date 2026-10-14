"""Translate Excel formulas into Python expressions.

Only a documented subset is supported. Anything else raises UnsupportedFormula, and
the caller records the reason instead of guessing.
"""

import re
from dataclasses import dataclass

SUPPORTED_FUNCTIONS = {
    "SUM", "AVERAGE", "MIN", "MAX", "COUNT", "IF", "ROUND", "ABS", "AND", "OR", "NOT",
}


class UnsupportedFormula(ValueError):
    pass


_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<string>"(?:[^"]|"")*")
  | (?P<xsheet>(?:'[^']+'|[A-Za-z_][\w.]*)!\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)
  | (?P<func>[A-Za-z][A-Za-z0-9.]*(?=\())
  | (?P<range>\$?[A-Za-z]{1,3}\$?\d+:\$?[A-Za-z]{1,3}\$?\d+)
  | (?P<ref>\$?[A-Za-z]{1,3}\$?\d+)
  | (?P<bool>TRUE|FALSE)(?![\w(])
  | (?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
  | (?P<op><>|<=|>=|[-+*/^&=<>])
  | (?P<lp>\()
  | (?P<rp>\))
  | (?P<comma>,)
    """,
    re.VERBOSE | re.IGNORECASE,
)

_CELL = re.compile(r"\$?([A-Za-z]{1,3})\$?(\d+)")


@dataclass(frozen=True)
class Token:
    kind: str
    text: str


def _tokenize(formula: str) -> list[Token]:
    tokens = []
    pos = 0
    while pos < len(formula):
        match = _TOKEN.match(formula, pos)
        if not match:
            raise UnsupportedFormula(f"syntax is not supported yet, near {formula[pos:pos + 12]!r}")
        pos = match.end()
        kind = match.lastgroup
        if kind == "ws":
            continue
        if kind == "xsheet":
            raise UnsupportedFormula("references to other sheets are not supported")
        tokens.append(Token(kind, match.group()))
    return tokens


def _column_index(letters: str) -> int:
    index = 0
    for ch in letters.upper():
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index - 1


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self, *kinds_or_texts):
        if self.pos >= len(self.tokens):
            return None
        tok = self.tokens[self.pos]
        for item in kinds_or_texts:
            if tok.kind == item or tok.text == item:
                return tok
        return None

    def take(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind):
        if not self.peek(kind):
            raise UnsupportedFormula(f"expected {kind} in formula")
        return self.take()

    def parse(self):
        node = self.comparison()
        if self.pos != len(self.tokens):
            raise UnsupportedFormula("unexpected text at the end of the formula")
        return node

    def _binary(self, operators, next_level):
        node = next_level()
        while True:
            tok = self.peek(*operators)
            if tok is None:
                return node
            self.take()
            node = ("bin", tok.text, node, next_level())

    def comparison(self):
        return self._binary(("=", "<>", "<", ">", "<=", ">="), self.concat)

    def concat(self):
        return self._binary(("&",), self.additive)

    def additive(self):
        return self._binary(("+", "-"), self.term)

    def term(self):
        return self._binary(("*", "/"), self.power)

    def power(self):
        # In Excel, negation binds before ^, so -2^2 is 4.
        return self._binary(("^",), self.negation)

    def negation(self):
        if self.peek("-"):
            self.take()
            return ("neg", self.negation())
        if self.peek("+"):
            self.take()
            return self.negation()
        return self.primary()

    def primary(self):
        tok = self.peek("number", "string", "bool", "ref", "range", "func", "lp")
        if tok is None:
            raise UnsupportedFormula("unexpected end of formula or unsupported syntax")
        self.take()
        if tok.kind == "number":
            return ("num", float(tok.text) if any(c in tok.text for c in ".eE") else int(tok.text))
        if tok.kind == "string":
            return ("str", tok.text[1:-1].replace('""', '"'))
        if tok.kind == "bool":
            return ("bool", tok.text.upper() == "TRUE")
        if tok.kind == "ref":
            return ("ref", tok.text)
        if tok.kind == "range":
            return ("range", tok.text)
        if tok.kind == "func":
            name = tok.text.upper()
            if name not in SUPPORTED_FUNCTIONS:
                raise UnsupportedFormula(f"function {name} is not supported yet")
            self.expect("lp")
            args = []
            if not self.peek("rp"):
                args.append(self.comparison())
                while self.peek("comma"):
                    self.take()
                    args.append(self.comparison())
            self.expect("rp")
            return ("call", name, args)
        # parenthesised expression
        node = self.comparison()
        self.expect("rp")
        return node


def _cell_python(ref: str, columns: list[str]) -> tuple[str, int]:
    match = _CELL.fullmatch(ref)
    if not match:
        raise UnsupportedFormula(f"cannot read cell reference {ref}")
    col = _column_index(match.group(1))
    if col >= len(columns):
        raise UnsupportedFormula(f"cell {ref} is outside the table")
    return columns[col], int(match.group(2))


def _emit(node, columns: list[str], used: set[str]) -> str:
    kind = node[0]
    if kind == "num":
        return repr(node[1])
    if kind == "str":
        return repr(node[1])
    if kind == "bool":
        return "True" if node[1] else "False"
    if kind == "ref":
        name, row = _cell_python(node[1], columns)
        used.add("cell")
        return f"cell(sheet, {name!r}, {row})"
    if kind == "range":
        start, end = node[1].split(":")
        start_name, start_row = _cell_python(start, columns)
        end_name, end_row = _cell_python(end, columns)
        if start_name != end_name:
            raise UnsupportedFormula("ranges across more than one column are not supported yet")
        used.add("rng")
        return f"rng(sheet, {start_name!r}, {start_row}, {end_row})"
    if kind == "neg":
        return f"(-{_emit(node[1], columns, used)})"
    if kind == "call":
        used.add(node[1])
        args = ", ".join(_emit(arg, columns, used) for arg in node[2])
        return f"{node[1]}({args})"
    if kind == "bin":
        op, left, right = node[1], _emit(node[2], columns, used), _emit(node[3], columns, used)
        if op == "&":
            used.add("concat")
            return f"concat({left}, {right})"
        if op == "^":
            return f"({left} ** {right})"
        if op == "=":
            return f"({left} == {right})"
        if op == "<>":
            return f"({left} != {right})"
        return f"({left} {op} {right})"
    raise UnsupportedFormula("unsupported syntax")


def translate(formula: str, columns: list[str]) -> tuple[str, set[str]]:
    """Return (python_expression, runtime_names_used) for an Excel formula string."""
    if not formula.startswith("="):
        raise UnsupportedFormula("not a formula")
    tree = _Parser(_tokenize(formula[1:])).parse()
    used: set[str] = set()
    return _emit(tree, columns, used), used


def script_for(formula: str, columns: list[str], target_column: str, row: int, sheet_title: str) -> str:
    """A complete Python script that computes the formula for one cell."""
    expression, used = translate(formula, columns)
    names = sorted(used)
    header = (
        f'"""Excel formula {formula} in sheet {sheet_title!r}, column {target_column!r}, row {row}.\n\n'
        'Generated by ai-xl2db. Blank cells count as 0 in arithmetic.\n"""\n'
    )
    imports = f"from ai_xl2db.runtime import {', '.join(names)}\n\n" if names else ""
    body = f"def compute(sheet):\n    return {expression}\n"
    return header + imports + "\n" + body
