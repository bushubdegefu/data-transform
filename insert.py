from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session

def execute_sql_file(
    session: Session,
    file_path: str
    ):
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    print(f"Reading SQL from {path}...")
    sql_content = path.read_text(encoding="utf-8")
    
    # Split into individual statements
    # This is a simple split by semicolon. For more complex SQL (e.g. with triggers/procedures), 
    # a more robust parser might be needed, but for simple INSERTs this is usually sufficient.
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    print(f"Found {len(statements)} statements to execute.")
    
    for statement in statements:
        session.execute(text(statement))
    print("All statements executed successfully.")