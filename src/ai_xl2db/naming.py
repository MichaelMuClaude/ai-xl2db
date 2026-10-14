"""Turn spreadsheet titles and headers into safe SQL identifiers."""

import re

_NON_WORD = re.compile(r"\W+", re.UNICODE)


def snake_case(text: str) -> str:
    """Lower-case the text and replace runs of punctuation and spaces with '_'."""
    cleaned = _NON_WORD.sub("_", text.strip().lower()).strip("_")
    return cleaned


def unique(name: str, taken: set[str]) -> str:
    """Return ``name``, or ``name_2``, ``name_3``... if it is already taken."""
    candidate = name
    counter = 2
    while candidate in taken:
        candidate = f"{name}_{counter}"
        counter += 1
    taken.add(candidate)
    return candidate


def table_name(sheet_title: str, taken: set[str]) -> str:
    name = snake_case(sheet_title) or "sheet"
    if name[0].isdigit():
        name = f"sheet_{name}"
    return unique(name, taken)


def column_names(headers: list[object]) -> list[str]:
    """Clean header cells. Empty headers become column_N; duplicates get a suffix."""
    taken: set[str] = set()
    names = []
    for index, header in enumerate(headers, start=1):
        name = snake_case(str(header)) if header is not None else ""
        if not name:
            name = f"column_{index}"
        elif name[0].isdigit():
            name = f"col_{name}"
        names.append(unique(name, taken))
    return names
