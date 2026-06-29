"""
transformation/cleaner.py
--------------------------
Data-cleaning utilities for PyAutoFlow.
Provides a composable pipeline of cleaning steps that can be applied
independently or chained together via ``clean_dataframe``.
"""

import pandas as pd
import numpy as np
from typing import Optional, List

from pyautoflow.utils import get_logger

logger = get_logger("transformation.cleaner")


def drop_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Remove exact duplicate rows from a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input data.
    subset : list[str], optional
        Columns to consider when identifying duplicates. If None, all
        columns are used.

    Returns
    -------
    pd.DataFrame
        DataFrame with duplicates removed.

    Examples
    --------
    >>> df = drop_duplicates(df, subset=["id", "date"])
    """
    before = len(df)
    df = df.drop_duplicates(subset=subset)
    removed = before - len(df)
    if removed:
        logger.debug(f"Removed {removed:,} duplicate rows")
    return df.reset_index(drop=True)


def handle_missing(
    df: pd.DataFrame,
    strategy: str = "drop",
    fill_value=None,
    numeric_strategy: str = "mean",
    threshold: float = 0.5,
) -> pd.DataFrame:
    """
    Handle missing (NaN) values in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input data.
    strategy : str
        One of:
        - ``'drop'``: drop rows with *any* NaN (default).
        - ``'fill'``: fill all NaNs with ``fill_value``.
        - ``'smart'``: numeric columns → ``numeric_strategy``; object columns → 'Unknown'.
        - ``'drop_col'``: drop columns where the fraction of NaN ≥ ``threshold``.
    fill_value : scalar, optional
        Constant used when ``strategy='fill'``.
    numeric_strategy : str
        Aggregation used for numeric imputation in 'smart' mode.
        One of ``'mean'``, ``'median'``, ``'zero'``.
    threshold : float
        Column NaN fraction threshold for ``'drop_col'`` strategy.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame.

    Examples
    --------
    >>> df = handle_missing(df, strategy="smart", numeric_strategy="median")
    """
    missing_count = df.isna().sum().sum()
    logger.debug(f"Missing values before cleaning: {missing_count:,}")

    if strategy == "drop":
        df = df.dropna()
    elif strategy == "fill":
        df = df.fillna(fill_value)
    elif strategy == "smart":
        for col in df.columns:
            if df[col].dtype in [np.float64, np.int64, float, int]:
                if numeric_strategy == "mean":
                    df[col] = df[col].fillna(df[col].mean())
                elif numeric_strategy == "median":
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna("Unknown")
    elif strategy == "drop_col":
        drop_cols = [c for c in df.columns if df[c].isna().mean() >= threshold]
        if drop_cols:
            logger.debug(f"Dropping high-NaN columns: {drop_cols}")
        df = df.drop(columns=drop_cols)

    logger.debug(f"Missing values after cleaning: {df.isna().sum().sum():,}")
    return df.reset_index(drop=True)


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise column names: lowercase, strip whitespace, replace spaces
    and special characters with underscores.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.

    Returns
    -------
    pd.DataFrame
        DataFrame with standardised column names.

    Examples
    --------
    >>> df = standardise_columns(df)  # "First Name " → "first_name"
    """
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-/]+", "_", regex=True)
        .str.replace(r"[^\w]", "", regex=True)
    )
    return df


def cast_dtypes(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Cast DataFrame columns to specified dtypes.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    schema : dict
        Mapping of column name → target dtype string.
        E.g. ``{"amount": "float64", "date": "datetime64[ns]", "id": "int32"}``.

    Returns
    -------
    pd.DataFrame
        DataFrame with applied type casts.

    Examples
    --------
    >>> df = cast_dtypes(df, {"revenue": "float64", "created_at": "datetime64[ns]"})
    """
    for col, dtype in schema.items():
        if col not in df.columns:
            logger.warning(f"Column '{col}' not found — skipping dtype cast")
            continue
        try:
            if "datetime" in dtype:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            else:
                df[col] = df[col].astype(dtype)
        except Exception as exc:
            logger.warning(f"Could not cast column '{col}' to {dtype}: {exc}")
    return df


def clean_dataframe(
    df: pd.DataFrame,
    standardise: bool = True,
    deduplicate: bool = True,
    missing_strategy: str = "smart",
    dtype_schema: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Run the full cleaning pipeline on a DataFrame.

    Steps (in order):
    1. Standardise column names (optional)
    2. Remove duplicates (optional)
    3. Handle missing values
    4. Cast dtypes (optional)

    Parameters
    ----------
    df : pd.DataFrame
        Raw input DataFrame.
    standardise : bool
        Whether to normalise column names (default: True).
    deduplicate : bool
        Whether to remove duplicate rows (default: True).
    missing_strategy : str
        Strategy passed to ``handle_missing`` (default: 'smart').
    dtype_schema : dict, optional
        Column dtype mapping passed to ``cast_dtypes``.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame ready for transformation.

    Examples
    --------
    >>> clean_df = clean_dataframe(raw_df, dtype_schema={"revenue": "float64"})
    """
    logger.info(f"Starting cleaning pipeline — {len(df):,} rows × {len(df.columns)} columns")

    if standardise:
        df = standardise_columns(df)
    if deduplicate:
        df = drop_duplicates(df)

    df = handle_missing(df, strategy=missing_strategy)

    if dtype_schema:
        df = cast_dtypes(df, dtype_schema)

    logger.info(f"Cleaning complete — {len(df):,} rows × {len(df.columns)} columns remaining")
    return df
