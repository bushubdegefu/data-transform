from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from typing import Any, Callable, Dict, Iterable, Mapping, Type

import pandas as pd
from sqlalchemy.orm import Session


def _resolve_model(model_spec: Any) -> Type:
    """
    Resolve a model reference from either:

    - a class/type object (returned as-is)
    - a string in the form "module.submodule:ClassName"

    This keeps the core transformer generic and free of hard-coded
    domain imports.
    """
    if isinstance(model_spec, type):
        return model_spec

    if isinstance(model_spec, str):
        try:
            module_path, class_name = model_spec.split(":", 1)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(
                "String model specification must be of the form "
                "'module.submodule:ClassName'"
            ) from exc

        module = import_module(module_path)
        try:
            return getattr(module, class_name)
        except AttributeError as exc:  # pragma: no cover - defensive
            raise ImportError(
                f"Could not find {class_name!r} in module {module_path!r}"
            ) from exc

    raise TypeError(
        f"Unsupported model specification type: {type(model_spec)!r}. "
        "Use a class or 'module:ClassName' string."
    )


def replace_column_with_lookup(
    df: pd.DataFrame,
    session: Session,
    model: Type | str,
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

    # Resolve model (class or "module:ClassName" string)
    model_cls = _resolve_model(model)

    # Build filter dynamically: model.lookup_field.in_(source_values)
    lookup_attr = getattr(model_cls, lookup_field)
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


# def add_missing_columns(
#     df: pd.DataFrame,
#     required_columns: Mapping[str, Any],
# ) -> pd.DataFrame:
#     """
#     Ensure that all required columns exist in the DataFrame, adding them
#     with default values if missing.

#     If the default value is callable, it will be called for each row to
#     populate the value (useful for datetime.utcnow, etc.).
#     """
#     for col, default in required_columns.items():
#         if col not in df.columns:
#             if callable(default):
#                 df[col] = [default() for _ in range(len(df))]
#             else:
#                 df[col] = default
#     return df


def add_missing_columns(df: pd.DataFrame, required_columns: Mapping[str, Any]) -> pd.DataFrame:
    """
    Ensure required columns exist and overwrite NaN or None values.

    - Callable defaults (e.g., datetime.utcnow) are called per row.
    - None defaults become "" (empty string).
    - Datetime values are converted to ISO strings.
    """
    for col, default in required_columns.items():

        # Always ensure the column exists
        if col not in df.columns:
            df[col] = None

        # Case 1: default is a callable like datetime.utcnow
        if callable(default):
            df[col] = df[col].apply(
                lambda v: default().isoformat()
                if pd.isna(v)
                else (v.isoformat() if isinstance(v, datetime) else v)
            )
            continue

        # Case 2: default is None → use empty string ""
        if default is None:
            df[col] = df[col].apply(
                lambda v: ""  if pd.isna(v) or v is None else v
            )
            continue

        # Case 3: default is a static value
        # Convert datetime -> ISO string if needed
        value = default.isoformat() if isinstance(default, datetime) else default

        # Fill NaN
        df[col] = df[col].fillna(value)

        # Convert stored datetime objects
        df[col] = df[col].apply(
            lambda v: v.isoformat() if isinstance(v, datetime) else v
        )

    return df

def filter_rows(
    df: pd.DataFrame,
    predicate: Callable[[Mapping[str, Any]], bool],
) -> pd.DataFrame:
    """
    Remove rows for which predicate(row) is False.

    The predicate receives a dict-like view of the row.
    """
    mask = df.apply(lambda row: bool(predicate(row)), axis=1)
    return df.loc[mask].reset_index(drop=True)

def replace_column_with_callable(
    df: pd.DataFrame,
    column: str,
    function: Callable[[Mapping[str, Any]], Any],
) -> pd.DataFrame:
    """
    Replace (or create) a column using a callable applied per row.

    The function receives a dict-like view of the row.
    """
    df[column] = df.apply(lambda row: function(row), axis=1)
    return df

def process_column_with_callable(
    df: pd.DataFrame,
    column: str,
    func: Callable[[Any], Any],
    new_column: str | None = None,
) -> pd.DataFrame:
    """
    Replace values in a column by applying a callable function.
    
    Parameters:
        df: DataFrame
        column: column to process
        func: function applied to each cell
        new_column: optional column name for result
    """
    if column not in df.columns:
        raise KeyError(f"Column {column!r} not found in DataFrame")
    
    target_col = new_column or column
    df[target_col] = df[column].map(func)
    return df


@dataclass
class TransformationConfig:
    """
    Declarative configuration for a sequence of transformations.
    This is mainly for convenience inside `config.py`.
    """

    # Built-in param-driven steps
    row_filters: list[Callable[[Mapping[str, Any]], bool]] | None = None
    replace_lookups: list[dict] | None = None
    remove_columns: list[str] | None = None
    computed_columns: list[dict] | None = None
    required_columns: dict | None = None
    replace_columns: list[dict] | None = None
    process_rows: list[Callable[[Mapping[str, Any]], bool]] | None = None

    # Fully generic hook: arbitrary callables taking (df, session) -> df
    custom_steps: list[Callable[[pd.DataFrame, Session], pd.DataFrame]] | None = None

    def apply(self, df: pd.DataFrame, session: Session) -> pd.DataFrame:
        """
        Apply configured transformations in a simple, generic pipeline:

        0. row_filters
        1. replace_lookups
        2. remove_columns
        3. computed_columns
        4. required_columns
        5. custom_steps
        6. replace_columns
        7. process_rows
        """

        # 0. Row filters (drop bad rows early)
        for predicate in self.row_filters or []:
            df = filter_rows(df, predicate)

        # 1. Replace lookups
        for cfg in self.replace_lookups or []:
            model_spec = cfg.get("model")
            if model_spec is None:
                raise ValueError("TransformationConfig.replace_lookups entry missing 'model'.")
            if session:
                df = replace_column_with_lookup(
                    df=df,
                    session=session,
                    model=model_spec,
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

        # 5. Arbitrary custom steps
        for step in self.custom_steps or []:
            df = step(df, session)

        # 6. Replace columns
        for cfg in self.replace_columns or []:
            df = replace_column_with_callable(
                df=df,
                column=cfg["column"],
                function=cfg["function"],
            ) 

        # proccess columns with callable      
        for cfg in self.replace_columns or []:
            df = process_column_with_callable(
                df=df,
                column=cfg["column"],
                func=cfg["func"],
                new_column=cfg.get("new_column")
            )   

        return df




