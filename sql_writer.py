from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


def _format_sql_value(value: Any) -> str:
    """Convert Python value into a SQL literal."""
    if value is None:
        return "NULL"

    if isinstance(value, (datetime, date)):
        return f"'{value.isoformat()}'"

    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, (int, float)):
        return str(value)

    # Fallback: treat as string, escape single quotes
    s = str(value).replace("'", "''")
    return f"'{s}'"


def dataframe_to_insert_statements(
    df: pd.DataFrame,
    table_name: str,
    columns: Iterable[str] | None = None,
) -> list[str]:
    """
    Convert a DataFrame into a list of SQL INSERT statements.

    Parameters
    ----------
    df : pandas.DataFrame
        Input data.
    table_name : str
        Target table name.
    columns : Iterable[str], optional
        Columns to include in the INSERT; defaults to all columns in df, in order.
    """
    if columns is None:
        columns = list(df.columns)
    else:
        columns = list(columns)

    col_list = ", ".join(columns)
    statements: list[str] = []

    for _, row in df.iterrows():
        values_sql = ", ".join(_format_sql_value(row[col]) for col in columns)
        stmt = f"INSERT INTO {table_name} ({col_list}) VALUES ({values_sql});"
        statements.append(stmt)

    return statements


def write_dataframe_as_inserts(
    df: pd.DataFrame,
    table_name: str,
    output_path: str | Path,
    columns: Iterable[str] | None = None,
) -> None:
    """
    Write DataFrame contents as INSERT statements to a file.
    """
    output_path = Path(output_path)
    statements = dataframe_to_insert_statements(df, table_name, columns=columns)
    text = "\n".join(statements) + ("\n" if statements else "")
    output_path.write_text(text, encoding="utf-8")


