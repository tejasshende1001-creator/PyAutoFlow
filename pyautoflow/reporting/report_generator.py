"""
reporting/report_generator.py
------------------------------
Report generation module for PyAutoFlow.
Writes pipeline results to CSV, JSON, and plain-text summary formats,
supporting configurable output directories and timestamped filenames.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from pyautoflow.utils import get_logger

logger = get_logger("reporting.generator")

SUPPORTED_FORMATS = ("csv", "json", "txt")


def _timestamp() -> str:
    """Return a compact ISO-8601 timestamp suitable for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_dir(path: str) -> None:
    """Create the output directory (and any parents) if it does not exist."""
    os.makedirs(path, exist_ok=True)


def save_csv(df: pd.DataFrame, filepath: str, index: bool = True) -> str:
    """
    Write a DataFrame to a CSV file.

    Parameters
    ----------
    df : pd.DataFrame
        Data to write.
    filepath : str
        Destination file path (created if absent).
    index : bool
        Whether to write the row index (default: True).

    Returns
    -------
    str
        Absolute path to the written file.

    Examples
    --------
    >>> path = save_csv(summary_df, "output/summary.csv")
    """
    _ensure_dir(os.path.dirname(filepath) or ".")
    df.to_csv(filepath, index=index)
    logger.info(f"CSV report saved → {filepath}  ({len(df):,} rows)")
    return os.path.abspath(filepath)


def save_json(df: pd.DataFrame, filepath: str, orient: str = "records", indent: int = 2) -> str:
    """
    Write a DataFrame to a JSON file.

    Parameters
    ----------
    df : pd.DataFrame
        Data to write.
    filepath : str
        Destination file path.
    orient : str
        Pandas JSON orientation (default: 'records').
    indent : int
        JSON indentation level.

    Returns
    -------
    str
        Absolute path to the written file.

    Examples
    --------
    >>> path = save_json(aggregated_df, "output/aggregated.json")
    """
    _ensure_dir(os.path.dirname(filepath) or ".")
    data = json.loads(df.to_json(orient=orient))
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    logger.info(f"JSON report saved → {filepath}  ({len(df):,} records)")
    return os.path.abspath(filepath)


def save_txt_summary(
    results: Dict[str, pd.DataFrame],
    filepath: str,
    title: str = "PyAutoFlow — Pipeline Report",
) -> str:
    """
    Write a human-readable plain-text summary of all pipeline results.

    Parameters
    ----------
    results : dict[str, pd.DataFrame]
        Output from ``run_pipeline``.
    filepath : str
        Destination ``.txt`` file path.
    title : str
        Report title displayed at the top.

    Returns
    -------
    str
        Absolute path to the written file.

    Examples
    --------
    >>> path = save_txt_summary(pipeline_results, "output/report.txt")
    """
    _ensure_dir(os.path.dirname(filepath) or ".")
    sep = "=" * 70
    thin = "-" * 70

    lines = [
        sep,
        f"  {title}",
        f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        sep,
        "",
    ]

    for name, df in results.items():
        lines += [
            f"[ {name.upper()} ]",
            thin,
            f"  Shape : {df.shape[0]:,} rows × {df.shape[1]} columns",
            f"  Columns: {', '.join(df.columns.tolist())}",
            "",
        ]
        # Show numeric snapshot
        num_df = df.select_dtypes(include="number")
        if not num_df.empty:
            lines.append("  Numeric snapshot:")
            for col in num_df.columns[:8]:          # cap at 8 cols
                col_data = num_df[col].dropna()
                if len(col_data):
                    lines.append(
                        f"    {col:<25} mean={col_data.mean():.4f}  "
                        f"min={col_data.min():.4f}  max={col_data.max():.4f}"
                    )
        lines += ["", thin, ""]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"TXT report saved → {filepath}")
    return os.path.abspath(filepath)


def generate_reports(
    results: Dict[str, pd.DataFrame],
    output_dir: str = "output",
    formats: List[str] = None,
    run_label: Optional[str] = None,
) -> Dict[str, List[str]]:
    """
    Generate all requested report formats for every pipeline result DataFrame.

    Parameters
    ----------
    results : dict[str, pd.DataFrame]
        Keyed collection of result DataFrames (from ``run_pipeline``).
    output_dir : str
        Directory where all report files will be written.
    formats : list[str], optional
        Subset of ``['csv', 'json', 'txt']`` to generate.
        Defaults to all three.
    run_label : str, optional
        Custom label used in filenames. Defaults to a timestamp.

    Returns
    -------
    dict[str, list[str]]
        Mapping of ``{format: [list_of_file_paths]}``.

    Examples
    --------
    >>> paths = generate_reports(pipeline_results, output_dir="output", formats=["csv", "json"])
    """
    if formats is None:
        formats = list(SUPPORTED_FORMATS)

    unknown = [f for f in formats if f not in SUPPORTED_FORMATS]
    if unknown:
        logger.warning(f"Unsupported formats ignored: {unknown}")
        formats = [f for f in formats if f in SUPPORTED_FORMATS]

    label = run_label or _timestamp()
    written: Dict[str, List[str]] = {fmt: [] for fmt in formats}

    logger.info(f"Generating reports → {output_dir}  formats={formats}  label='{label}'")

    for result_name, df in results.items():
        if df.empty:
            logger.warning(f"Skipping empty result '{result_name}'")
            continue

        base = os.path.join(output_dir, f"{result_name}_{label}")

        if "csv" in formats:
            path = save_csv(df, f"{base}.csv")
            written["csv"].append(path)

        if "json" in formats:
            path = save_json(df, f"{base}.json")
            written["json"].append(path)

    if "txt" in formats:
        txt_path = os.path.join(output_dir, f"pipeline_report_{label}.txt")
        path = save_txt_summary(results, txt_path)
        written["txt"].append(path)

    total = sum(len(v) for v in written.values())
    logger.info(f"Report generation complete — {total} file(s) written to '{output_dir}'")
    return written
