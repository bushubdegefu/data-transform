from pathlib import Path
from typing import Union

import pandas as pd


def load_excel_to_dataframe(path: Union[str, Path]) -> pd.DataFrame:
    """
    Load an Excel file (.xlsx) into a pandas DataFrame.

    Parameters
    ----------
    path : str or Path
        Path to the Excel file.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    # Read the first sheet by default
    df = pd.read_excel(path, engine="openpyxl")
    return df


