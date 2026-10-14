"""Check that a stored script only does what the translator generates.

The scripts are plain Python. Before one is run, its syntax tree must contain only
the constructs the translator produces: one function, calls to the runtime helpers,
arithmetic, comparisons, and literals. Anything else is refused. This is a guard
against mistakes and edits, not a sandbox for hostile code.
"""

import ast

from ai_xl2db import runtime

ALLOWED_CALLS = {
    "SUM", "AVERAGE", "MIN", "MAX", "COUNT", "IF", "ROUND", "ABS", "AND", "OR", "NOT",
    "cell", "rng", "concat",
}

_ALLOWED_NODES = (
    ast.Module, ast.ImportFrom, ast.alias, ast.FunctionDef, ast.arguments, ast.arg,
    ast.Return, ast.Expr, ast.Call, ast.Name, ast.Load, ast.Constant, ast.BinOp,
    ast.UnaryOp, ast.Compare, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
    ast.USub, ast.UAdd, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


def validate(source: str) -> None:
    """Raise ValueError if the script contains anything the translator would not produce."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"script does not parse: {exc}") from exc

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "compute":
        raise ValueError("script must define exactly one function, compute(sheet)")

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            raise ValueError("scripts may only import from ai_xl2db.runtime")
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"script uses {type(node).__name__}, which is not allowed")
        if isinstance(node, ast.ImportFrom):
            if node.module != "ai_xl2db.runtime":
                raise ValueError("scripts may only import from ai_xl2db.runtime")
            for alias in node.names:
                if alias.name not in ALLOWED_CALLS:
                    raise ValueError(f"import of {alias.name} is not allowed")
                imported.add(alias.name)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS:
                raise ValueError("script calls a function that is not allowed")
            if node.func.id not in imported:
                raise ValueError(f"{node.func.id} is called without being imported")
        if isinstance(node, ast.Name) and node.id not in ALLOWED_CALLS and node.id != "sheet":
            raise ValueError(f"script uses the name {node.id!r}, which is not allowed")


def _import_runtime_only(name, globals=None, locals=None, fromlist=(), level=0):
    if name != "ai_xl2db.runtime" or level != 0:
        raise ImportError(f"scripts may only import from ai_xl2db.runtime, not {name}")
    return runtime


def run(source: str, sheet):
    """Validate a script, then return the value of its compute(sheet) function."""
    validate(source)
    namespace = {"__builtins__": {"__import__": _import_runtime_only}}
    exec(compile(source, "<stored formula>", "exec"), namespace)  # validated above
    return namespace["compute"](sheet)


assert all(hasattr(runtime, name) for name in ALLOWED_CALLS), "every allowed name must exist in runtime"
