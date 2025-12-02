from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import pandas as pd

from config import get_transformation_for_table
from db import get_session
from excel_loader import load_excel_to_dataframe
from sql_loader import load_sql_inserts_to_dataframe
from sql_writer import write_dataframe_as_inserts


def _detect_input_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return "excel"
    if ext == ".sql":
        return "sql"
    raise ValueError(f"Unsupported input file type: {ext}")


def load_input(path: Path, table_name: str) -> Tuple[pd.DataFrame, str]:
    input_type = _detect_input_type(path)
    if input_type == "excel":
        df = load_excel_to_dataframe(path)
        return df, table_name
    else:
        df, detected_table = load_sql_inserts_to_dataframe(path, expected_table=None)
        return df, detected_table


def run_etl(input_file: str, table_name: str, output_file: str) -> None:
    input_path = Path(input_file)
    output_path = Path(output_file)

    df, detected_table = load_input(input_path, table_name)

    # Use the CLI-provided table_name for output, but pass detected_table to config
    target_table_for_output = table_name or detected_table

    with get_session() as session:
        config = get_transformation_for_table(target_table_for_output, session)
        if config is not None:
            df = config.apply(df, session)

        write_dataframe_as_inserts(df, target_table_for_output, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic ETL-style tool for transforming tabular data into SQL INSERTs."
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to input file (.xlsx or .sql).",
    )
    parser.add_argument(
        "--table-name",
        required=True,
        help="Target table name for output INSERT statements.",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to write cleaned SQL INSERT statements.",
    )

    args = parser.parse_args()
    run_etl(args.input_file, args.table_name, args.output_file)


if __name__ == "__main__":
    main()


