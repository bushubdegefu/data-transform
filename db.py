from contextlib import contextmanager
import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

load_dotenv()

DATABASE_URL_IMPORT = os.getenv("DATABASE_URL_IMPORT", "postgresql+psycopg://user:password@localhost/dbname",)

DATABASE_URL_EXPORT = os.getenv("DATABASE_URL_EXPORT", "postgresql+psycopg://user:password@localhost/dbname")
print(f"Import Database URL: {DATABASE_URL_IMPORT}")
print(f"Export Database URL: {DATABASE_URL_EXPORT}")

# engine_import = create_engine(DATABASE_URL_IMPORT, echo=False, future=True, connect_args={"ssl": {"check_hostname": False}})
engine_import = create_engine(DATABASE_URL_IMPORT, echo=False, future=True)
engine_export = create_engine(DATABASE_URL_EXPORT, echo=False, future=True)    

SessionLocal_import = sessionmaker(bind=engine_import, autoflush=False, autocommit=False, future=True)
SessionLocal_export = sessionmaker(bind=engine_export, autoflush=False, autocommit=False, future=True)

Base_import = declarative_base()
Base_export = declarative_base()


@contextmanager
def get_session_import() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session: Session = SessionLocal_import()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@contextmanager
def get_session_export() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session: Session = SessionLocal_export()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


