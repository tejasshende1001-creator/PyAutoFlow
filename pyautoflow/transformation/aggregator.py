"""
transformation/aggregator.py
-----------------------------
NumPy-accelerated aggregation and statistical summary functions for PyAutoFlow.
Provides column-level and group-level aggregations that significantly outperform
naive Python loops on large datasets.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any

from pyautoflow.utils import get_logger

logger = get_logger("transformation.aggregator")


def numeric_summary(df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Compute a statistical summary table for numeric columns using NumPy.

    For each selected column the function calculates:
    count, mean, std, min, 25th, 50th, 75th percentile, max, sum, and variance.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    columns : list[str], optional
        Subset of numeric columns to summarise. Defaults to all numeric
        columns in the DataFrame.

    Returns
    -------
    pd.DataFrame
        Summary table with one row per column.

    Examples
    --------
    >>> summary = numeric_summary(df, columns=["revenue", "units"])
    >>> print(summary)
    """
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if columns:
        num_cols = [c for c in columns if c in num_cols]

    if not num_cols:
        logger.warning("No numeric columns found for summary")
        return pd.DataFrame()

    rows = []
    for col in num_cols:
        arr = df[col].dropna().to_numpy(dtype=np.float64)
        rows.append({
            "column":      col,
            "count":       int(len(arr)),
            "mean":        np.mean(arr),
            "std":         np.std(arr, ddof=1) if len(arr) > 1 else 0.0,
            "min":         np.min(arr),
            "p25":         np.percentile(arr, 25),
            "p50":         np.percentile(arr, 50),
            "p75":         np.percentile(arr, 75),
            "max":         np.max(arr),
            "sum":         np.sum(arr),
            "variance":    np.var(arr, ddof=1) if len(arr) > 1 else 0.0,
        })

    logger.info(f"Computed numeric summary for {len(rows)} column(s)")
    return pd.DataFrame(rows).set_index("column")


def group_aggregate(
    df: pd.DataFrame,
    group_by: List[str],
    agg_map: Dict[str, Any],
) -> pd.DataFrame:
    """
    Apply group-level aggregations defined by ``agg_map``.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    group_by : list[str]
        Columns to group by.
    agg_map : dict
        Mapping of ``{column: aggregation_function_or_string}``.
        Supports any Pandas-compatible agg string ('sum', 'mean', 'max', …)
        or a callable accepting a Series.

    Returns
    -------
    pd.DataFrame
        Grouped and aggregated DataFrame with reset index.

    Examples
    --------
    >>> result = group_aggregate(
    ...     df,
    ...     group_by=["region", "category"],
    ...     agg_map={"revenue": "sum", "units": "mean", "orders": "count"},
    ... )
    """
    missing_cols = [c for c in group_by + list(agg_map.keys()) if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Columns not found in DataFrame: {missing_cols}")

    logger.info(f"Aggregating by {group_by} → {list(agg_map.keys())}")
    result = df.groupby(group_by).agg(agg_map).reset_index()
    result.columns = [
        "_".join(filter(None, [str(c) for c in col])) if isinstance(col, tuple) else col
        for col in result.columns
    ]
    logger.info(f"Aggregation produced {len(result):,} groups")
    return result


def rolling_stats(
    df: pd.DataFrame,
    value_col: str,
    window: int = 7,
    date_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute rolling mean and rolling standard deviation for a value column.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame (must be sorted by ``date_col`` if provided).
    value_col : str
        The numeric column to compute rolling statistics on.
    window : int
        Rolling window size in rows (default: 7).
    date_col : str, optional
        If provided, the DataFrame is sorted by this column first.

    Returns
    -------
    pd.DataFrame
        Original DataFrame with two new columns:
        ``{value_col}_rolling_mean`` and ``{value_col}_rolling_std``.

    Examples
    --------
    >>> df = rolling_stats(df, value_col="sales", window=7, date_col="date")
    """
    if date_col and date_col in df.columns:
        df = df.sort_values(date_col).reset_index(drop=True)

    df[f"{value_col}_rolling_mean"] = (
        df[value_col].rolling(window=window, min_periods=1).mean()
    )
    df[f"{value_col}_rolling_std"] = (
        df[value_col].rolling(window=window, min_periods=1).std().fillna(0.0)
    )
    logger.debug(f"Rolling stats (window={window}) added for '{value_col}'")
    return df


def detect_outliers_iqr(
    df: pd.DataFrame,
    column: str,
    multiplier: float = 1.5,
) -> pd.DataFrame:
    """
    Flag outliers using the IQR (Interquartile Range) method with NumPy.

    A new boolean column ``{column}_is_outlier`` is added to the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        Numeric column to inspect.
    multiplier : float
        IQR fence multiplier (default: 1.5 → Tukey fences).

    Returns
    -------
    pd.DataFrame
        DataFrame with a new ``{column}_is_outlier`` boolean column.

    Examples
    --------
    >>> df = detect_outliers_iqr(df, column="revenue", multiplier=1.5)
    >>> outliers = df[df["revenue_is_outlier"]]
    """
    arr = df[column].to_numpy(dtype=np.float64)
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
    df[f"{column}_is_outlier"] = (arr < lower) | (arr > upper)
    n_outliers = df[f"{column}_is_outlier"].sum()
    logger.info(f"Outlier detection on '{column}': {n_outliers:,} flagged "
                f"(IQR×{multiplier}, fence=[{lower:.2f}, {upper:.2f}])")
    return df
