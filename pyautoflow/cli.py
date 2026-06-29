"""
cli.py
------
Command-line interface for PyAutoFlow.
Parses arguments, wires up the ingestion → transformation → reporting
pipeline, and prints a final summary table to stdout.

Usage examples
--------------
  # Process a CSV file with default settings
  python -m pyautoflow.cli --input data/sample_input.csv

  # Process JSON with group aggregation and multiple report formats
  python -m pyautoflow.cli --input data/sample_input.json \\
      --group-by category --agg revenue:sum units:mean \\
      --formats csv json txt

  # Fetch live data from the bundled demo API endpoint
  python -m pyautoflow.cli --source api --api-endpoint posts \\
      --formats csv txt

  # Full pipeline with filters and derived columns
  python -m pyautoflow.cli --input data/sample_input.csv \\
      --filter "units > 5" "revenue > 0" \\
      --derive "profit=revenue - cost" \\
      --group-by region --agg revenue:sum \\
      --outlier-col revenue \\
      --formats csv json txt
"""

import argparse
import sys

from pyautoflow.utils import get_logger, Config
from pyautoflow.ingestion import load_csv, load_json, fetch_api_data
from pyautoflow.transformation import run_pipeline
from pyautoflow.reporting import generate_reports

logger = get_logger("cli")


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="pyautoflow",
        description=(
            "PyAutoFlow — Python-Based Workflow Automation & Reporting Tool\n"
            "Ingest CSV/JSON/API data → transform → generate reports."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Source ────────────────────────────────────────────────────────────────
    src_group = parser.add_argument_group("Data Source")
    src_group.add_argument(
        "--source",
        choices=["file", "api"],
        default="file",
        help="Data source type (default: file)",
    )
    src_group.add_argument(
        "--input",
        metavar="PATH",
        help="Path to input CSV or JSON file (required when --source=file)",
    )
    src_group.add_argument(
        "--api-endpoint",
        metavar="ENDPOINT",
        default="posts",
        help="API endpoint name appended to the base URL (default: posts)",
    )
    src_group.add_argument(
        "--api-limit",
        type=int,
        default=100,
        metavar="N",
        help="Max records to fetch from the API (default: 100)",
    )

    # ── Pipeline ──────────────────────────────────────────────────────────────
    pipe_group = parser.add_argument_group("Transformation Pipeline")
    pipe_group.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip the data-cleaning stage",
    )
    pipe_group.add_argument(
        "--missing-strategy",
        choices=["smart", "drop", "fill"],
        default="smart",
        help="Strategy for missing values (default: smart)",
    )
    pipe_group.add_argument(
        "--filter",
        nargs="+",
        metavar="EXPR",
        dest="filters",
        help='Pandas query expressions for row filtering (e.g. "revenue > 0")',
    )
    pipe_group.add_argument(
        "--derive",
        nargs="+",
        metavar="COL=EXPR",
        dest="derivations",
        help='Derived column definitions (e.g. "profit=revenue - cost")',
    )
    pipe_group.add_argument(
        "--group-by",
        nargs="+",
        metavar="COL",
        help="Columns to group by for aggregation",
    )
    pipe_group.add_argument(
        "--agg",
        nargs="+",
        metavar="COL:FUNC",
        help='Aggregations (e.g. "revenue:sum" "units:mean")',
    )
    pipe_group.add_argument(
        "--rolling-col",
        metavar="COL",
        help="Column for rolling mean/std computation",
    )
    pipe_group.add_argument(
        "--rolling-window",
        type=int,
        default=7,
        metavar="N",
        help="Rolling window size (default: 7)",
    )
    pipe_group.add_argument(
        "--outlier-col",
        metavar="COL",
        help="Column for IQR-based outlier detection",
    )
    pipe_group.add_argument(
        "--outlier-multiplier",
        type=float,
        default=1.5,
        help="IQR fence multiplier (default: 1.5)",
    )

    # ── Output ────────────────────────────────────────────────────────────────
    out_group = parser.add_argument_group("Output")
    out_group.add_argument(
        "--output-dir",
        default="output",
        metavar="DIR",
        help="Directory for generated reports (default: output/)",
    )
    out_group.add_argument(
        "--formats",
        nargs="+",
        choices=["csv", "json", "txt"],
        default=["csv", "json", "txt"],
        metavar="FMT",
        help="Report formats to generate (default: csv json txt)",
    )
    out_group.add_argument(
        "--label",
        metavar="LABEL",
        help="Custom label for report filenames (default: timestamp)",
    )

    # ── Config ────────────────────────────────────────────────────────────────
    cfg_group = parser.add_argument_group("Configuration")
    cfg_group.add_argument(
        "--config",
        default="config.json",
        metavar="FILE",
        help="Path to JSON config file (default: config.json)",
    )
    cfg_group.add_argument(
        "--version",
        action="version",
        version="PyAutoFlow 1.0.0",
    )

    return parser


# ─────────────────────────────────────────────────────────────────────────────
# Helper parsers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_derivations(raw: list) -> dict:
    """Parse ['profit=revenue - cost', ...] into {'profit': 'revenue - cost', ...}."""
    result = {}
    for item in raw:
        if "=" not in item:
            logger.warning(f"Skipping invalid derivation (no '='): '{item}'")
            continue
        col, expr = item.split("=", 1)
        result[col.strip()] = expr.strip()
    return result


def _parse_agg_map(raw: list) -> dict:
    """Parse ['revenue:sum', 'units:mean'] into {'revenue': 'sum', 'units': 'mean'}."""
    result = {}
    for item in raw:
        if ":" not in item:
            logger.warning(f"Skipping invalid aggregation (no ':'): '{item}'")
            continue
        col, func = item.split(":", 1)
        result[col.strip()] = func.strip()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    """
    Entry point for the PyAutoFlow CLI.

    Parameters
    ----------
    argv : list, optional
        Argument list (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 = success, 1 = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = Config.from_file(args.config)

    # ── Ingest ────────────────────────────────────────────────────────────────
    try:
        if args.source == "api":
            url = f"{cfg.api_base_url}/{args.api_endpoint}"
            logger.info(f"Fetching live data from API: {url}")
            df = fetch_api_data(url, params={"_limit": args.api_limit}, timeout=cfg.api_timeout)
        else:
            if not args.input:
                parser.error("--input is required when --source=file")
            path = args.input
            if path.lower().endswith(".json"):
                df = load_json(path)
            else:
                df = load_csv(path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(f"Ingestion failed: {exc}")
        return 1

    # ── Transform ─────────────────────────────────────────────────────────────
    derivations = _parse_derivations(args.derivations) if args.derivations else None
    agg_map     = _parse_agg_map(args.agg)             if args.agg         else None

    try:
        results = run_pipeline(
            df,
            clean=not args.no_clean,
            missing_strategy=args.missing_strategy,
            filters=args.filters,
            derivations=derivations,
            group_by=args.group_by,
            agg_map=agg_map,
            rolling_col=args.rolling_col,
            rolling_window=args.rolling_window,
            outlier_col=args.outlier_col,
            outlier_multiplier=args.outlier_multiplier,
        )
    except Exception as exc:
        logger.error(f"Pipeline failed: {exc}")
        return 1

    # ── Report ────────────────────────────────────────────────────────────────
    written = generate_reports(
        results,
        output_dir=args.output_dir,
        formats=args.formats,
        run_label=args.label,
    )

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PyAutoFlow — Run Complete")
    print("=" * 60)
    for stage, df_result in results.items():
        print(f"  [{stage:<12}] {df_result.shape[0]:>6,} rows × {df_result.shape[1]} cols")
    print("-" * 60)
    total_files = sum(len(v) for v in written.values())
    print(f"  Reports written : {total_files} file(s) -> '{args.output_dir}/'")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
