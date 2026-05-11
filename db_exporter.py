from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


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


def export_table_to_csv(
    session: Session,
    table_name: str,
    output_path: str | Path,
    columns: list[str] | None = None,
) -> None:
    """
    Export a database table to a CSV file.

    Parameters
    ----------
    session : Session
        Active database session.
    table_name : str
        Name of the table to export.
    output_path : str or Path
        Path to the output CSV file.
    columns : list[str], optional
        Specific columns to export. If None, exports all columns.
    """
    output_path = Path(output_path)
    
    # Build query
    if columns:
        cols = ", ".join(columns)
        query = f"SELECT {cols} FROM {table_name}"
    else:
        query = f"SELECT * FROM {table_name}"
    
    # Execute and fetch as DataFrame
    df = pd.read_sql(text(query), session.bind)
    
    # Write to CSV
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Exported {len(df)} rows to {output_path}")


def export_table_to_sql(
    session: Session,
    table_name: str,
    output_path: str | Path,
    columns: list[str] | None = None,
    batch_size: int = 1000,
) -> None:
    """
    Export a database table to a SQL file with batched INSERT statements.

    Parameters
    ----------
    session : Session
        Active database session.
    table_name : str
        Name of the table to export.
    output_path : str or Path
        Path to the output SQL file.
    columns : list[str], optional
        Specific columns to export. If None, exports all columns.
    batch_size : int, default=1000
        Number of rows to include in each INSERT statement.
    """
    output_path = Path(output_path)
    
    # Build query
    if columns:
        cols = ", ".join(columns)
        query = f"SELECT {cols} FROM {table_name}"
    else:
        query = f"SELECT * FROM {table_name}"
    
    # Execute and fetch as DataFrame
    df = pd.read_sql(text(query), session.bind)
    
    if df.empty:
        output_path.write_text("", encoding="utf-8")
        print(f"No rows to export from {table_name}")
        return
    
    # Get column names
    if columns is None:
        columns = list(df.columns)
    
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
    
    # Write to file
    text_content = "\n\n".join(statements) + "\n"
    output_path.write_text(text_content, encoding="utf-8")
    print(f"Exported {len(df)} rows in {len(statements)} batched INSERT statements to {output_path}")


def export_table(
    session: Session,
    table_name: str,
    output_path: str | Path,
    format: str = "sql",
    columns: list[str] | None = None,
    batch_size: int = 1000,
) -> None:
    """
    Export a database table to either SQL or CSV format.

    Parameters
    ----------
    session : Session
        Active database session.
    table_name : str
        Name of the table to export.
    output_path : str or Path
        Path to the output file.
    format : str, default="sql"
        Export format: "sql" or "csv".
    columns : list[str], optional
        Specific columns to export. If None, exports all columns.
    batch_size : int, default=1000
        Number of rows per INSERT statement (only used for SQL format).
    """
    if format.lower() == "csv":
        export_table_to_csv(session, table_name, output_path, columns)
    elif format.lower() == "sql":
        export_table_to_sql(session, table_name, output_path, columns, batch_size)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'sql' or 'csv'.")


def export(
    table_name: str,
    export_path: str | Path | None = None,
    format: str = "sql",
    columns: list[str] | None = None,
    batch_size: int = 1000,
) -> None:
    """
    Generic exporter function that handles session management automatically.
    
    Exports a database table to SQL or CSV format with sensible defaults.

    Parameters
    ----------
    table_name : str
        Name of the table to export.
    export_path : str or Path, optional
        Path to the output file. If None, defaults to "exported/{table_name}.{format}".
    format : str, default="sql"
        Export format: "sql" or "csv".
    columns : list[str], optional
        Specific columns to export. If None, exports all columns.
    batch_size : int, default=1000
        Number of rows per INSERT statement (only used for SQL format).
    
    Examples
    --------
    >>> # Export to default location (exported/customers.sql)
    >>> export("customers")
    
    >>> # Export to CSV with custom path
    >>> export("customers", "data/customers.csv", format="csv")
    
    >>> # Export with custom batch size
    >>> export("orders", batch_size=500)
    """
    from db import get_session
    
    # Set default export path
    if export_path is None:
        export_dir = Path("exported")
        export_dir.mkdir(exist_ok=True)
        export_path = export_dir / f"{table_name}.{format}"
    else:
        export_path = Path(export_path)
        # Create parent directory if it doesn't exist
        export_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use session context manager
    with get_session() as session:
        export_table(
            session=session,
            table_name=table_name,
            output_path=export_path,
            format=format,
            columns=columns,
            batch_size=batch_size,
        )
