"""
ingestion/json_reader.py
------------------------
JSON ingestion module for PyAutoFlow.
Handles flat JSON arrays, nested records, and newline-delimited JSON (NDJSON).
"""

import json
import os
import pandas as pd
from typing import Optional

from pyautoflow.utils import get_logger

logger = get_logger("ingestion.json")


def load_json(
    filepath: str,
    record_path: Optional[list] = None,
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """
    Load a JSON file into a Pandas DataFrame.

    Supports:
    - Flat JSON arrays: ``[{...}, {...}]``
    - Nested records via ``record_path``
    - Newline-delimited JSON (NDJSON / JSON Lines)

    Parameters
    ----------
    filepath : str
        Path to the JSON file.
    record_path : list, optional
        Key path to reach the list of records inside a nested object.
        E.g. ``["data", "items"]`` for ``{"data": {"items": [...]}}``.
    encoding : str
        File encoding (default: 'utf-8').

    Returns
    -------
    pd.DataFrame
        Normalised DataFrame from the JSON source.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the JSON cannot be normalised into a tabular structure.

    Examples
    --------
    >>> df = load_json("data/events.json")
    >>> df = load_json("data/nested.json", record_path=["results"])
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    logger.info(f"Loading JSON → {filepath}")

    with open(filepath, "r", encoding=encoding) as f:
        content = f.read().strip()

    # Auto-detect NDJSON (newline-delimited JSON)
    if content.startswith("{") and "\n" in content:
        logger.debug("Detected NDJSON format")
        records = [json.loads(line) for line in content.splitlines() if line.strip()]
        df = pd.DataFrame(records)
    else:
        raw = json.loads(content)
        if record_path:
            for key in record_path:
                raw = raw[key]
        df = pd.json_normalize(raw)

    if df.empty:
        raise ValueError(f"JSON file produced an empty DataFrame: {filepath}")

    logger.info(f"Loaded {len(df):,} records × {len(df.columns)} columns from '{os.path.basename(filepath)}'")
    return df


def load_json_from_dict(data: dict, record_path: Optional[list] = None) -> pd.DataFrame:
    """
    Normalise an in-memory Python dict or list into a DataFrame.

    Parameters
    ----------
    data : dict or list
        The already-parsed JSON payload (e.g., from an API response).
    record_path : list, optional
        Key path to the list of records within a nested dict.

    Returns
    -------
    pd.DataFrame
        Normalised DataFrame.

    Examples
    --------
    >>> api_payload = {"results": [{"id": 1, "value": 99}]}
    >>> df = load_json_from_dict(api_payload, record_path=["results"])
    """
    if record_path:
        for key in record_path:
            data = data[key]
    df = pd.json_normalize(data)
    logger.debug(f"Normalised in-memory payload → {len(df):,} rows × {len(df.columns)} columns")
    return df
