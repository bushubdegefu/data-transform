from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session


def import_sql_file(
    session: Session,
    sql_file_path: str | Path,
) -> int:
    """
    Import SQL statements from a file and execute them.

    Parameters
    ----------
    session : Session
        Active database session.
    sql_file_path : str or Path
        Path to the SQL file containing INSERT statements.

    Returns
    -------
    int
        Number of statements executed.
    """
    sql_file_path = Path(sql_file_path)
    
    if not sql_file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
    
    print(f"Reading SQL from {sql_file_path}...")
    sql_content = sql_file_path.read_text(encoding="utf-8")
    
    # Split into individual statements
    # Simple split by semicolon works for standard INSERT statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    print(f"Found {len(statements)} statements to execute.")
    
    # Execute each statement
    for statement in statements:
        session.execute(text(statement))
    
    print(f"Successfully executed {len(statements)} statements.")
    return len(statements)


def import_sql(
    sql_file_path: str | Path | None = None,
    table_name: str | None = None,
) -> int:
    """
    Generic import function that handles session management automatically.
    
    Imports SQL statements from a file into the database.

    Parameters
    ----------
    sql_file_path : str or Path, optional
        Path to the SQL file. If None and table_name is provided, 
        defaults to "exported/{table_name}.sql".
    table_name : str, optional
        Table name to construct default path. Only used if sql_file_path is None.

    Returns
    -------
    int
        Number of statements executed.
    
    Examples
    --------
    >>> # Import from default location (exported/customers.sql)
    >>> import_sql(table_name="customers")
    
    >>> # Import from custom path
    >>> import_sql("data/customers.sql")
    
    >>> # Import using explicit path
    >>> import_sql(sql_file_path="backup/orders.sql")
    """
    from db import get_session
    
    # Determine SQL file path
    if sql_file_path is None:
        if table_name is None:
            raise ValueError("Either sql_file_path or table_name must be provided")
        sql_file_path = Path("exported") / f"{table_name}.sql"
    else:
        sql_file_path = Path(sql_file_path)
    
    # Use session context manager
    with get_session() as session:
        count = import_sql_file(session, sql_file_path)
    
    return count
