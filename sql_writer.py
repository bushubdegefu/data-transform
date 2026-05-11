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


def dataframe_to_batched_inserts(
    df: pd.DataFrame,
    table_name: str,
    batch_size: int = 1000,
    columns: Iterable[str] | None = None,
) -> list[str]:
    """
    Convert a DataFrame into batched SQL INSERT statements.
    
    Each statement contains multiple rows (up to batch_size) in a single INSERT.

    Parameters
    ----------
    df : pandas.DataFrame
        Input data.
    table_name : str
        Target table name.
    batch_size : int, default=1000
        Number of rows to include in each INSERT statement.
    columns : Iterable[str], optional
        Columns to include in the INSERT; defaults to all columns in df, in order.
    
    Returns
    -------
    list[str]
        List of batched INSERT statements.
    """
    if df.empty:
        return []
    
    if columns is None:
        columns = list(df.columns)
    else:
        columns = list(columns)
    
    col_list = ", ".join(columns)
    statements = []
    
    # Generate batched INSERT statements
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        
        # Build VALUES clause for this batch
        values_rows = []
        for _, row in batch.iterrows():
            values_sql = ", ".join(_format_sql_value(row[col]) for col in columns)
            values_rows.append(f"({values_sql})")
        
        # Combine into single INSERT statement
        values_clause = ",\n    ".join(values_rows)
        stmt = f"INSERT INTO {table_name} ({col_list}) VALUES\n    {values_clause};"
        statements.append(stmt)
    
    return statements


def write_dataframe_as_batched_inserts(
    df: pd.DataFrame,
    table_name: str,
    output_path: str | Path,
    batch_size: int = 1000,
    columns: Iterable[str] | None = None,
) -> None:
    """
    Write DataFrame contents as batched INSERT statements to a file.
    
    Parameters
    ----------
    df : pandas.DataFrame
        Input data.
    table_name : str
        Target table name.
    output_path : str or Path
        Path to the output SQL file.
    batch_size : int, default=1000
        Number of rows to include in each INSERT statement.
    columns : Iterable[str], optional
        Columns to include in the INSERT; defaults to all columns in df, in order.
    """
    output_path = Path(output_path)
    statements = dataframe_to_batched_inserts(df, table_name, batch_size, columns)
    text = "\n\n".join(statements) + ("\n" if statements else "")
    output_path.write_text(text, encoding="utf-8")


def csv_to_sql(
    csv_path: str | Path,
    table_name: str,
    output_path: str | Path | None = None,
    batch_size: int = 1000,
    columns: list[str] | None = None,
) -> None:
    """
    Convert a CSV file to SQL INSERT statements.
    
    Generic helper function that reads a CSV and generates batched INSERT statements.

    Parameters
    ----------
    csv_path : str or Path
        Path to the input CSV file.
    table_name : str
        Target table name for INSERT statements.
    output_path : str or Path, optional
        Path to the output SQL file. If None, defaults to same directory as CSV
        with .sql extension.
    batch_size : int, default=1000
        Number of rows to include in each INSERT statement.
    columns : list[str], optional
        Specific columns to include. If None, includes all columns from CSV.
    
    Examples
    --------
    >>> # Convert CSV to SQL with default settings
    >>> csv_to_sql("data/customers.csv", "customers")
    
    >>> # Custom output path and batch size
    >>> csv_to_sql("data/orders.csv", "orders", "sql/orders.sql", batch_size=500)
    
    >>> # Only specific columns
    >>> csv_to_sql("data/users.csv", "users", columns=["id", "name", "email"])
    """
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Set default output path
    if output_path is None:
        output_path = csv_path.with_suffix(".sql")
    else:
        output_path = Path(output_path)
    
    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read CSV
    print(f"Reading CSV from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Filter columns if specified
    if columns:
        df = df[columns]
    
    print(f"Converting {len(df)} rows to SQL INSERT statements...")
    
    # Write batched INSERT statements
    write_dataframe_as_batched_inserts(df, table_name, output_path, batch_size)
    
    num_batches = (len(df) + batch_size - 1) // batch_size
    print(f"Wrote {num_batches} batched INSERT statements to {output_path}")


