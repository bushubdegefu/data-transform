from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, Mapping, Type

import pandas as pd
from sqlalchemy.orm import Session


def replace_column_with_lookup(
    df: pd.DataFrame,
    session: Session,
    model: Type,
    source_column: str,
    lookup_field: str,
    return_field: str,
    new_column_name: str | None = None,
) -> pd.DataFrame:
    """
    Replace values in a column by looking them up from the database.

    Example:
        replace_column_with_lookup(
            df,
            session,
            Customer,
            source_column="customer_tin",
            lookup_field="tin",
            return_field="id",
            new_column_name="customer_id",
        )

    The function will:
    - Query the DB for all distinct values of `source_column`
    - Build a mapping from lookup_field -> return_field
    - Map the column and either overwrite or create `new_column_name`
    """
    if source_column not in df.columns:
        raise KeyError(f"Source column {source_column!r} not found in DataFrame.")

    new_col = new_column_name or source_column

    source_values = df[source_column].dropna().unique().tolist()
    if not source_values:
        # Nothing to replace
        if new_col != source_column:
            df[new_col] = None
        return df

    # Build filter dynamically: model.lookup_field.in_(source_values)
    lookup_attr = getattr(model, lookup_field)
    return_attr = getattr(model, return_field)

    results = (
        session.query(lookup_attr, return_attr)
        .filter(lookup_attr.in_(source_values))
        .all()
    )

    mapping: Dict[Any, Any] = {lookup_val: return_val for lookup_val, return_val in results}

    def _lookup(value: Any) -> Any:
        if value is None:
            return None
        return mapping.get(value)

    df[new_col] = df[source_column].map(_lookup)
    return df


def remove_columns(df: pd.DataFrame, column_list: Iterable[str]) -> pd.DataFrame:
    """
    Remove unwanted columns if they exist.
    """
    cols_to_drop = [c for c in column_list if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
    return df


def add_computed_column(
    df: pd.DataFrame,
    new_column: str,
    function: Callable[[Mapping[str, Any]], Any],
) -> pd.DataFrame:
    """
    Add a new computed column based on a row-wise function.

    The function receives a dict-like view of the row.
    """
    df[new_column] = df.apply(lambda row: function(row), axis=1)
    return df


def add_missing_columns(
    df: pd.DataFrame,
    required_columns: Mapping[str, Any],
) -> pd.DataFrame:
    """
    Ensure that all required columns exist in the DataFrame, adding them
    with default values if missing.

    If the default value is callable, it will be called for each row to
    populate the value (useful for datetime.utcnow, etc.).
    """
    for col, default in required_columns.items():
        if col not in df.columns:
            if callable(default):
                df[col] = [default() for _ in range(len(df))]
            else:
                df[col] = default
    return df


@dataclass
class TransformationConfig:
    """
    Declarative configuration for a sequence of transformations.
    This is mainly for convenience inside `config.py`.
    """

    replace_lookups: list[dict] | None = None
    remove_columns: list[str] | None = None
    computed_columns: list[dict] | None = None
    required_columns: dict | None = None

    def apply(self, df: pd.DataFrame, session: Session) -> pd.DataFrame:
        # 1. Replace lookups
        for cfg in self.replace_lookups or []:
            model = cfg.get("model")
            if model is None:
                raise ValueError("TransformationConfig.replace_lookups entry missing 'model'.")
            if not isinstance(model, type):
                raise TypeError(
                    f"'model' in replace_lookups must be a class/type, got {type(model)!r}"
                )

            df = replace_column_with_lookup(
                df=df,
                session=session,
                model=model,
                source_column=cfg["source_column"],
                lookup_field=cfg["lookup_field"],
                return_field=cfg["return_field"],
                new_column_name=cfg.get("new_column_name"),
            )

        # 2. Remove columns
        if self.remove_columns:
            df = remove_columns(df, self.remove_columns)

        # 3. Computed columns
        for comp in self.computed_columns or []:
            new_col = comp["new_column"]
            func = comp["function"]
            df = add_computed_column(df, new_col, func)

        # 4. Required columns
        if self.required_columns:
            df = add_missing_columns(df, self.required_columns)

        return df


def default_customers_transformation() -> TransformationConfig:
    """
    Example transformation configuration for the `customers` table.
    """

    from models import Customer

    def full_name_func(row: Mapping[str, Any]) -> str:
        # For this domain, we treat customer_name as the full display name.
        name = row.get("customer_name") or ""
        return str(name).strip()

    return TransformationConfig(
        replace_lookups=[
            {
                # Input column coming from Excel/SQL export
                "source_column": "customer_tin",
                "model": Customer,
                # Database column name on the Customer model
                "lookup_field": "tin_number",
                "return_field": "id",
                "new_column_name": "customer_id",
            }
        ],
        remove_columns=["temp_column", "unused_flag"],
        computed_columns=[
            {
                "new_column": "full_name",
                "function": full_name_func,
            }
        ],
        required_columns={
            "created_at": datetime.utcnow,
        },
    )


