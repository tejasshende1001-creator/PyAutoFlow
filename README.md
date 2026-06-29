# PyAutoFlow 🔄

> **Python-Based Workflow Automation & Reporting Tool** — 2025–2026

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-green)](https://pandas.pydata.org)
[![NumPy](https://img.shields.io/badge/NumPy-1.26%2B-orange)](https://numpy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)](#running-tests)

PyAutoFlow is a modular, command-line Python tool that automates repetitive data processing workflows. It ingests raw **CSV and JSON** inputs, applies **Pandas/NumPy transformation logic**, fetches **live REST API data**, and generates structured **summary reports** — all without manual intervention.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Multi-source Ingestion** | CSV (full + chunked streaming), JSON (flat/nested/NDJSON), REST API |
| **Smart Data Cleaning** | Dedup, missing-value strategies (smart/drop/fill), column standardisation, dtype casting |
| **NumPy Aggregations** | Statistical summaries, group aggregations, rolling stats, IQR outlier detection |
| **Derived Columns** | Add computed columns via Pandas `eval` expressions |
| **Row Filtering** | Chain Pandas query conditions for precise row selection |
| **Multi-format Reporting** | CSV, JSON, and human-readable TXT reports, all timestamped |
| **REST API Integration** | Auto-retry, bearer-token auth, pagination support |
| **Unit Tests** | Full pytest suite with coverage reporting |
| **Shell Wrappers** | `run.sh` (Bash/Zsh) and `run.ps1` (PowerShell/Windows) |

---

## 📁 Project Structure

```
PyAutoFlow/
├── pyautoflow/
│   ├── __init__.py
│   ├── cli.py                      # Argparse CLI entry point
│   ├── ingestion/
│   │   ├── csv_reader.py           # load_csv(), stream_csv()
│   │   ├── json_reader.py          # load_json(), load_json_from_dict()
│   │   └── api_fetcher.py          # fetch_api_data(), fetch_paginated()
│   ├── transformation/
│   │   ├── cleaner.py              # clean_dataframe() pipeline
│   │   ├── aggregator.py           # NumPy-backed stats & aggregations
│   │   └── transformer.py          # run_pipeline() orchestrator
│   ├── reporting/
│   │   └── report_generator.py     # generate_reports() → CSV/JSON/TXT
│   └── utils/
│       ├── logger.py               # Colorised logger
│       └── config.py               # Config dataclass
├── tests/
│   ├── test_ingestion.py
│   ├── test_transformation.py
│   └── test_reporting.py
├── data/
│   ├── sample_input.csv
│   └── sample_input.json
├── output/                         # Generated reports land here
├── logs/                           # Log files
├── config.json                     # Default configuration
├── requirements.txt
├── setup.py
├── run.sh                          # Bash wrapper
└── run.ps1                         # PowerShell wrapper
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/PyAutoFlow.git
cd PyAutoFlow
pip install -r requirements.txt
# Or install as a package:
pip install -e .
```

### 2. Run the Full Demo Pipeline (CSV)

```bash
# Bash / macOS / Linux
./run.sh full

# Windows PowerShell
.\run.ps1 full
```

### 3. Run Individual Workflows

```bash
# Process a CSV file
python -m pyautoflow.cli --input data/sample_input.csv

# Process a JSON file
python -m pyautoflow.cli --input data/sample_input.json

# Fetch live data from REST API
python -m pyautoflow.cli --source api --api-endpoint posts --api-limit 50
```

---

## 💻 CLI Reference

```
usage: pyautoflow [-h] [--source {file,api}] [--input PATH]
                  [--api-endpoint ENDPOINT] [--api-limit N]
                  [--no-clean] [--missing-strategy {smart,drop,fill}]
                  [--filter EXPR [EXPR ...]] [--derive COL=EXPR [COL=EXPR ...]]
                  [--group-by COL [COL ...]] [--agg COL:FUNC [COL:FUNC ...]]
                  [--rolling-col COL] [--rolling-window N]
                  [--outlier-col COL] [--outlier-multiplier MULTIPLIER]
                  [--output-dir DIR] [--formats {csv,json,txt} ...]
                  [--label LABEL] [--config FILE] [--version]
```

### Examples

```bash
# 1. Process CSV with group aggregation and outlier detection
python -m pyautoflow.cli \
    --input data/sample_input.csv \
    --group-by region category \
    --agg revenue:sum units:mean \
    --outlier-col revenue \
    --formats csv json txt

# 2. Add derived columns and filter rows
python -m pyautoflow.cli \
    --input data/sample_input.csv \
    --filter "units > 5" "revenue > 0" \
    --derive "profit=revenue - cost" "margin_pct=profit / revenue * 100" \
    --group-by region \
    --agg profit:sum \
    --formats csv txt

# 3. Rolling statistics on time-series data
python -m pyautoflow.cli \
    --input data/sample_input.csv \
    --rolling-col revenue \
    --rolling-window 7 \
    --formats csv

# 4. Fetch and report on live API data
python -m pyautoflow.cli \
    --source api \
    --api-endpoint posts \
    --api-limit 100 \
    --formats csv json txt

# 5. Chunk-stream a large CSV (used internally; accessible via Python API)
python -c "
from pyautoflow.ingestion import stream_csv
for chunk in stream_csv('data/sample_input.csv', chunk_size=5):
    print(chunk.shape)
"
```

---

## 🐍 Python API

Use PyAutoFlow as a library inside your own scripts:

```python
from pyautoflow.ingestion import load_csv, fetch_api_data
from pyautoflow.transformation import run_pipeline
from pyautoflow.reporting import generate_reports

# 1. Ingest
df = load_csv("data/sample_input.csv", parse_dates=["date"])

# 2. Transform
results = run_pipeline(
    df,
    missing_strategy="smart",
    filters=["units > 5"],
    derivations={"profit": "revenue - cost"},
    group_by=["region", "category"],
    agg_map={"revenue": "sum", "profit": "sum", "units": "mean"},
    outlier_col="revenue",
)

# 3. Report
generate_reports(results, output_dir="output", formats=["csv", "json", "txt"])
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=pyautoflow --cov-report=term-missing

# Run a single test module
pytest tests/test_transformation.py -v

# Using the shell wrapper
./run.sh test        # Bash
.\run.ps1 test       # PowerShell
```

---

## ⚙️ Configuration

Edit `config.json` to customise defaults:

```json
{
  "input_dir":      "data",
  "output_dir":     "output",
  "log_dir":        "logs",
  "api_base_url":   "https://your-api.example.com",
  "api_timeout":    30,
  "report_formats": ["csv", "json", "txt"],
  "chunk_size":     10000,
  "decimal_places": 4
}
```

**Environment variable overrides** (highest priority):

| Variable | Description |
|---|---|
| `PYAUTOFLOW_API_KEY` | Bearer token for REST API authentication |
| `PYAUTOFLOW_API_URL` | Override the API base URL |

---

## 📊 Pipeline Stages

```
Input (CSV / JSON / API)
        │
        ▼
┌─────────────────┐
│  1. Ingest      │  load_csv / load_json / fetch_api_data
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Clean       │  dedup → handle_missing → standardise → cast_dtypes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Filter      │  pandas query conditions (ANDed)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Derive      │  add computed columns via eval()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Aggregate   │  groupby + agg_map (NumPy-backed)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. Rolling     │  rolling mean / std on value column
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  7. Outliers    │  IQR fence detection (NumPy)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  8. Report  CSV · JSON · TXT    │  generate_reports()
└─────────────────────────────────┘
```

---

## 🛠️ Tech Stack

- **Python 3.10+** — Core language
- **Pandas 2.0+** — DataFrame ingestion, cleaning, filtering, aggregation
- **NumPy 1.26+** — Vectorised statistical operations and outlier detection
- **Requests** — HTTP client with retry/backoff for REST API integration
- **pytest + pytest-cov** — Unit testing and coverage
- **Bash / PowerShell** — Shell script wrappers for automation

---

## 📄 License

MIT © PyAutoFlow Contributors
