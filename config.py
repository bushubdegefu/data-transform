"""
Transformation configuration for different tables.

This file is intended to stay as domain-specific as possible while keeping
the core engine (`transformer.py`, `sql_loader.py`, `excel_loader.py`,
`sql_writer.py`) fully generic.
"""

from __future__ import annotations

from typing import Callable, Dict

from sqlalchemy.orm import Session

from transformer import TransformationConfig, default_customers_transformation


# Mapping of table name -> callable that returns a TransformationConfig.
# You can add more table-specific transformations here without touching
# the core engine.
TABLE_TRANSFORMS: Dict[str, Callable[[], TransformationConfig]] = {
    "customers": default_customers_transformation,
}


def get_transformation_for_table(
    table_name: str,
    session: Session,  # kept here for potential advanced use-cases
) -> TransformationConfig | None:
    """
    Return a TransformationConfig for the given table name, if any.

    For now this simply looks up TABLE_TRANSFORMS and calls the factory.
    The `session` parameter is provided to make it easier to build more
    complex, dynamic configurations in the future if needed.
    """
    factory = TABLE_TRANSFORMS.get(table_name.lower())
    if not factory:
        return None
    return factory()


