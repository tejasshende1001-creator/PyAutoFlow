"""
ingestion/csv_reader.py
-----------------------
CSV ingestion module for PyAutoFlow.
Supports full-file loading and memory-efficient chunked streaming for
large datasets.
"""

import os
import pandas as pd
from typing import Iterator, Optional

from pyautoflow.utils import get_logger

logger = get_logger("ingestion.csv")


def load_csv(
    filepath: str,
    dtype: Optional[dict] = None,
    parse_dates: Optional[list] = None,
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """
    Load an entire CSV file into a Pandas DataFrame.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the CSV file.
    dtype : dict, optional
        Column-to-dtype mapping passed directly to ``pd.read_csv``.
    parse_dates : list, optional
        List of column names to parse as datetime objects.
    encoding : str
        File encoding (default: 'utf-8').

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with all rows loaded.

    Raises
    ------
    FileNotFoundError
        If the file does not exist at the given path.
    ValueError
        If the file is empty or cannot be parsed as CSV.

    Examples
    --------
    >>> df = load_csv("data/sales.csv", parse_dates=["date"])
    >>> print(df.shape)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    logger.info(f"Loading CSV → {filepath}")
    df = pd.read_csv(filepath, dtype=dtype, parse_dates=parse_dates, encoding=encoding)

    if df.empty:
        raise ValueError(f"CSV file is empty: {filepath}")

    logger.info(f"Loaded {len(df):,} rows × {len(df.columns)} columns from '{os.path.basename(filepath)}'")
    return df


def stream_csv(
    filepath: str,
    chunk_size: int = 10_000,
    dtype: Optional[dict] = None,
    encoding: str = "utf-8",
) -> Iterator[pd.DataFrame]:
    """
    Yield chunks of a CSV file as DataFrames for memory-efficient processing.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.
    chunk_size : int
        Number of rows per chunk (default: 10,000).
    dtype : dict, optional
        Column dtype overrides.
    encoding : str
        File encoding.

    Yields
    ------
    pd.DataFrame
        A chunk of ``chunk_size`` rows (last chunk may be smaller).

    Examples
    --------
    >>> for chunk in stream_csv("data/large_file.csv", chunk_size=5000):
    ...     process(chunk)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    logger.info(f"Streaming CSV in chunks of {chunk_size:,} → {filepath}")
    reader = pd.read_csv(filepath, chunksize=chunk_size, dtype=dtype, encoding=encoding)
    for i, chunk in enumerate(reader, start=1):
        logger.debug(f"  Chunk {i}: {len(chunk):,} rows")
        yield chunk
