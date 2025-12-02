import re
from pathlib import Path
from typing import List, Tuple, Union

import pandas as pd


INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+(?P<table>\w+)\s*"
    r"\((?P<columns>[^)]+)\)\s*"
    r"VALUES\s*\((?P<values>[^)]+)\)\s*;",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_values(values_str: str) -> List[str]:
    """
    Parse the VALUES part of an INSERT statement into a list of values.

    Handles:
    - single-quoted strings with escaped quotes
    - numeric literals
    - NULL
    """
    tokens: List[str] = []
    current = []
    in_string = False
    escape_next = False

    for ch in values_str:
        if in_string:
            if escape_next:
                current.append(ch)
                escape_next = False
            elif ch == "\\":
                escape_next = True
            elif ch == "'":
                in_string = False
                current.append(ch)
            else:
                current.append(ch)
        else:
            if ch == "'":
                in_string = True
                current.append(ch)
            elif ch == ",":
                token = "".join(current).strip()
                if token:
                    tokens.append(token)
                current = []
            else:
                current.append(ch)

    if current:
        tokens.append("".join(current).strip())

    return tokens


def _clean_sql_value(token: str):
    """Convert a raw SQL token to a Python value."""
    upper = token.upper()
    if upper == "NULL":
        return None

    if token.startswith("'") and token.endswith("'"):
        inner = token[1:-1]
        # Unescape simple backslash-escapes of quotes
        inner = inner.replace("\\'", "'")
        inner = inner.replace('\\"', '"')
        return inner

    # Try integer
    try:
        return int(token)
    except ValueError:
        pass

    # Try float
    try:
        return float(token)
    except ValueError:
        pass

    return token


def load_sql_inserts_to_dataframe(
    path: Union[str, Path], expected_table: str | None = None
) -> Tuple[pd.DataFrame, str]:
    """
    Parse a SQL file containing simple INSERT statements into a DataFrame.

    Parameters
    ----------
    path : str or Path
        Path to the SQL file.
    expected_table : str, optional
        If provided, validate that INSERT statements all target this table.

    Returns
    -------
    df : pandas.DataFrame
        DataFrame containing parsed rows.
    table_name : str
        The table name discovered from the first INSERT.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")

    text = path.read_text(encoding="utf-8")

    rows = []
    table_name_detected: str | None = None
    columns: List[str] | None = None

    for match in INSERT_RE.finditer(text):
        table = match.group("table")
        cols_str = match.group("columns")
        vals_str = match.group("values")

        if table_name_detected is None:
            table_name_detected = table
        elif table_name_detected != table:
            raise ValueError(
                f"Multiple tables detected in SQL file: {table_name_detected} and {table}"
            )

        if expected_table and table.lower() != expected_table.lower():
            raise ValueError(
                f"INSERT target table {table!r} does not match expected {expected_table!r}"
            )

        if columns is None:
            columns = [c.strip() for c in cols_str.split(",")]

        value_tokens = _parse_values(vals_str)
        if len(value_tokens) != len(columns):
            raise ValueError(
                f"Column/value mismatch: {len(columns)} columns, {len(value_tokens)} values in: {match.group(0)!r}"
            )

        row = {col: _clean_sql_value(tok) for col, tok in zip(columns, value_tokens)}
        rows.append(row)

    if not rows:
        raise ValueError("No INSERT statements found in SQL file.")

    df = pd.DataFrame(rows, columns=columns)
    assert table_name_detected is not None
    return df, table_name_detected


