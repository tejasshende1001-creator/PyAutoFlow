"""
transformation/transformer.py
------------------------------
High-level transformation pipeline for PyAutoFlow.
Composes cleaning, aggregation, and enrichment steps into a single,
configurable ``run_pipeline`` entry point.
"""

import pandas as pd
from typing import List, Optional, Dict, Any

from pyautoflow.utils import get_logger
from pyautoflow.transformation.cleaner import clean_dataframe
from pyautoflow.transformation.aggregator import (
    numeric_summary,
    group_aggregate,
    rolling_stats,
    detect_outliers_iqr,
)

logger = get_logger("transformation.transformer")


def add_derived_columns(df: pd.DataFrame, derivations: Dict[str, str]) -> pd.DataFrame:
    """
    Add new columns derived from existing ones via Pandas ``eval``.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    derivations : dict
        Mapping of ``{new_column_name: expression_string}``.
        The expression is evaluated with ``df.eval()``.

    Returns
    -------
    pd.DataFrame
        DataFrame with additional derived columns.

    Examples
    --------
    >>> df = add_derived_columns(df, {
    ...     "profit": "revenue - cost",
    ...     "margin_pct": "profit / revenue * 100",
    ... })
    """
    for col, expr in derivations.items():
        try:
            df[col] = df.eval(expr)
            logger.debug(f"  Derived '{col}' = '{expr}'")
        except Exception as exc:
            logger.warning(f"Could not derive '{col}' from '{expr}': {exc}")
    return df


def filter_rows(df: pd.DataFrame, conditions: List[str]) -> pd.DataFrame:
    """
    Filter DataFrame rows using a list of Pandas query strings.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    conditions : list[str]
        List of query expressions ANDed together.
        E.g. ``["revenue > 0", "region != 'Unknown'"]``.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with reset index.

    Examples
    --------
    >>> df = filter_rows(df, ["units > 0", "category == 'Electronics'"])
    """
    before = len(df)
    for cond in conditions:
        try:
            df = df.query(cond)
        except Exception as exc:
            logger.warning(f"Filter condition '{cond}' failed: {exc}")
    removed = before - len(df)
    logger.debug(f"Row filter removed {removed:,} rows ({before:,} → {len(df):,})")
    return df.reset_index(drop=True)


def run_pipeline(
    df: pd.DataFrame,
    clean: bool = True,
    missing_strategy: str = "smart",
    dtype_schema: Optional[dict] = None,
    filters: Optional[List[str]] = None,
    derivations: Optional[Dict[str, str]] = None,
    group_by: Optional[List[str]] = None,
    agg_map: Optional[Dict[str, Any]] = None,
    rolling_col: Optional[str] = None,
    rolling_window: int = 7,
    outlier_col: Optional[str] = None,
    outlier_multiplier: float = 1.5,
) -> Dict[str, pd.DataFrame]:
    """
    Execute the full PyAutoFlow transformation pipeline and return a
    dictionary of result DataFrames.

    Pipeline stages:
    1. **Clean** — dedup, handle missing, standardise columns, cast dtypes
    2. **Filter** — apply row-level query conditions
    3. **Derive** — add computed columns via expressions
    4. **Aggregate** — group-level aggregations
    5. **Rolling** — rolling mean / std on a time-series column
    6. **Outliers** — IQR-based outlier flagging

    Parameters
    ----------
    df : pd.DataFrame
        Raw input DataFrame.
    clean : bool
        Run the cleaning stage (default: True).
    missing_strategy : str
        Missing-value strategy for the cleaner ('smart', 'drop', 'fill').
    dtype_schema : dict, optional
        Column dtype overrides applied during cleaning.
    filters : list[str], optional
        Pandas query strings for row filtering.
    derivations : dict, optional
        ``{new_col: expression}`` pairs for derived columns.
    group_by : list[str], optional
        Columns to group by for aggregation.
    agg_map : dict, optional
        ``{column: agg_function}`` pairs applied per group.
    rolling_col : str, optional
        Column for rolling statistics.
    rolling_window : int
        Window size for rolling stats (default: 7).
    outlier_col : str, optional
        Column for IQR outlier detection.
    outlier_multiplier : float
        IQR fence multiplier (default: 1.5).

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary with keys:
        - ``'clean'``: cleaned (and filtered/derived) data
        - ``'summary'``: numeric statistical summary
        - ``'aggregated'``: group aggregation result (if requested)
        - ``'rolling'``: rolling stats result (if requested)
        - ``'outliers'``: subset of rows flagged as outliers (if requested)

    Examples
    --------
    >>> results = run_pipeline(
    ...     df,
    ...     group_by=["region"],
    ...     agg_map={"revenue": "sum", "units": "mean"},
    ...     outlier_col="revenue",
    ... )
    >>> results["aggregated"].head()
    """
    results: Dict[str, pd.DataFrame] = {}

    logger.info("=" * 60)
    logger.info("PyAutoFlow Transformation Pipeline Starting")
    logger.info("=" * 60)

    # ── Stage 1: Clean ──────────────────────────────────────────────
    if clean:
        df = clean_dataframe(df, missing_strategy=missing_strategy, dtype_schema=dtype_schema)

    # ── Stage 2: Filter ─────────────────────────────────────────────
    if filters:
        df = filter_rows(df, filters)

    # ── Stage 3: Derive ─────────────────────────────────────────────
    if derivations:
        df = add_derived_columns(df, derivations)

    results["clean"] = df.copy()

    # ── Stage 4: Summary ────────────────────────────────────────────
    results["summary"] = numeric_summary(df)

    # ── Stage 5: Aggregate ──────────────────────────────────────────
    if group_by and agg_map:
        results["aggregated"] = group_aggregate(df, group_by, agg_map)

    # ── Stage 6: Rolling ────────────────────────────────────────────
    if rolling_col and rolling_col in df.columns:
        results["rolling"] = rolling_stats(df.copy(), rolling_col, window=rolling_window)

    # ── Stage 7: Outliers ───────────────────────────────────────────
    if outlier_col and outlier_col in df.columns:
        flagged = detect_outliers_iqr(df.copy(), outlier_col, multiplier=outlier_multiplier)
        results["outliers"] = flagged[flagged[f"{outlier_col}_is_outlier"]]

    logger.info("Pipeline complete — stages produced: " + ", ".join(f"'{k}'" for k in results))
    return results
