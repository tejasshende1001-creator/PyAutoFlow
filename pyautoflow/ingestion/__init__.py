"""
ingestion/__init__.py
"""
from .csv_reader import load_csv, stream_csv
from .json_reader import load_json, load_json_from_dict
from .api_fetcher import fetch_api_data, fetch_paginated

__all__ = [
    "load_csv", "stream_csv",
    "load_json", "load_json_from_dict",
    "fetch_api_data", "fetch_paginated",
]
