"""
ingestion/api_fetcher.py
------------------------
REST API data-fetching module for PyAutoFlow.
Wraps requests with retry logic, timeout handling, bearer-token auth,
and automatic DataFrame normalisation of JSON responses.
"""

import time
from typing import Optional, Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pyautoflow.utils import get_logger
from pyautoflow.ingestion.json_reader import load_json_from_dict

logger = get_logger("ingestion.api")


def _build_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
) -> requests.Session:
    """
    Build a requests.Session with automatic retry logic.

    Parameters
    ----------
    retries : int
        Maximum number of retry attempts.
    backoff_factor : float
        Exponential back-off factor between retries.
    status_forcelist : tuple
        HTTP status codes that trigger a retry.

    Returns
    -------
    requests.Session
        Configured session object.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_api_data(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    api_key: Optional[str] = None,
    timeout: int = 30,
    record_path: Optional[list] = None,
) -> pd.DataFrame:
    """
    Fetch JSON data from a REST API endpoint and return a DataFrame.

    Parameters
    ----------
    url : str
        Full URL of the API endpoint.
    params : dict, optional
        Query-string parameters appended to the URL.
    headers : dict, optional
        Additional HTTP headers (merged with defaults).
    api_key : str, optional
        Bearer token sent in the ``Authorization`` header.
    timeout : int
        Request timeout in seconds (default: 30).
    record_path : list, optional
        Nested key path to the list of records in the JSON response body.

    Returns
    -------
    pd.DataFrame
        Normalised DataFrame from the API response.

    Raises
    ------
    requests.HTTPError
        If the server returns a 4xx or 5xx response.
    ValueError
        If the response body is not valid JSON or cannot be tabularised.

    Examples
    --------
    >>> df = fetch_api_data(
    ...     url="https://jsonplaceholder.typicode.com/posts",
    ...     params={"_limit": 50},
    ... )
    >>> print(df.head())
    """
    default_headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        default_headers["Authorization"] = f"Bearer {api_key}"
    if headers:
        default_headers.update(headers)

    session = _build_session()
    logger.info(f"GET {url}  params={params}")

    t0 = time.perf_counter()
    response = session.get(url, params=params, headers=default_headers, timeout=timeout)
    elapsed = time.perf_counter() - t0

    response.raise_for_status()
    logger.info(f"Response {response.status_code} in {elapsed:.3f}s — {len(response.content):,} bytes")

    payload = response.json()
    df = load_json_from_dict(payload, record_path=record_path)
    logger.info(f"API → {len(df):,} records fetched from '{url}'")
    return df


def fetch_paginated(
    base_url: str,
    page_param: str = "_page",
    limit_param: str = "_limit",
    page_size: int = 100,
    max_pages: int = 10,
    params: Optional[dict] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Paginate through a REST API and concatenate all pages into one DataFrame.

    Parameters
    ----------
    base_url : str
        API endpoint URL.
    page_param : str
        Query-param name for the page number (default: '_page').
    limit_param : str
        Query-param name for the page size (default: '_limit').
    page_size : int
        Number of records per page.
    max_pages : int
        Safety cap on the maximum pages to fetch.
    params : dict, optional
        Additional static query parameters.
    **kwargs
        Forwarded to ``fetch_api_data``.

    Returns
    -------
    pd.DataFrame
        Concatenated DataFrame of all pages.

    Examples
    --------
    >>> df = fetch_paginated("https://jsonplaceholder.typicode.com/posts", page_size=10, max_pages=5)
    """
    frames = []
    base_params = dict(params or {})
    base_params[limit_param] = page_size

    for page in range(1, max_pages + 1):
        base_params[page_param] = page
        logger.debug(f"Fetching page {page}/{max_pages}")
        chunk = fetch_api_data(base_url, params=dict(base_params), **kwargs)
        if chunk.empty:
            logger.info(f"Empty page at page={page}. Stopping pagination.")
            break
        frames.append(chunk)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    logger.info(f"Pagination complete — {len(result):,} total records across {len(frames)} page(s)")
    return result
