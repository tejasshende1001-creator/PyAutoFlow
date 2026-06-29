"""
tests/test_ingestion.py
------------------------
Unit tests for the PyAutoFlow ingestion layer.
Tests cover CSV loading, JSON loading, streaming, and in-memory dict normalisation.
"""

import os
import json
import pytest
import pandas as pd

from pyautoflow.ingestion.csv_reader import load_csv, stream_csv
from pyautoflow.ingestion.json_reader import load_json, load_json_from_dict


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_csv(tmp_path) -> str:
    """Write a small CSV to a temp directory and return its path."""
    path = tmp_path / "sample.csv"
    path.write_text(
        "id,name,region,revenue,units\n"
        "1,Alice,North,1500.0,10\n"
        "2,Bob,South,2300.5,25\n"
        "3,Carol,North,800.0,8\n"
        "4,Dave,East,3200.0,40\n",
        encoding="utf-8",
    )
    return str(path)


@pytest.fixture
def sample_json(tmp_path) -> str:
    """Write a flat JSON array to a temp directory and return its path."""
    data = [
        {"id": 1, "product": "Widget", "price": 9.99, "qty": 5},
        {"id": 2, "product": "Gadget", "price": 24.99, "qty": 2},
    ]
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


@pytest.fixture
def nested_json(tmp_path) -> str:
    """Write a nested JSON file with a record_path."""
    data = {"results": [{"id": 10, "score": 88}, {"id": 11, "score": 95}]}
    path = tmp_path / "nested.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


# ─────────────────────────────────────────────────────────────────────────────
# CSV Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadCsv:
    def test_returns_dataframe(self, sample_csv):
        df = load_csv(sample_csv)
        assert isinstance(df, pd.DataFrame)

    def test_correct_shape(self, sample_csv):
        df = load_csv(sample_csv)
        assert df.shape == (4, 5)

    def test_column_names(self, sample_csv):
        df = load_csv(sample_csv)
        assert list(df.columns) == ["id", "name", "region", "revenue", "units"]

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_csv("/nonexistent/path/file.csv")

    def test_empty_csv_raises(self, tmp_path):
        empty = tmp_path / "empty.csv"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ValueError):
            load_csv(str(empty))

    def test_revenue_dtype_float(self, sample_csv):
        df = load_csv(sample_csv)
        assert df["revenue"].dtype == float


class TestStreamCsv:
    def test_yields_chunks(self, sample_csv):
        chunks = list(stream_csv(sample_csv, chunk_size=2))
        assert len(chunks) == 2

    def test_total_rows(self, sample_csv):
        total = sum(len(c) for c in stream_csv(sample_csv, chunk_size=2))
        assert total == 4

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            list(stream_csv("/bad/path.csv"))


# ─────────────────────────────────────────────────────────────────────────────
# JSON Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadJson:
    def test_returns_dataframe(self, sample_json):
        df = load_json(sample_json)
        assert isinstance(df, pd.DataFrame)

    def test_correct_shape(self, sample_json):
        df = load_json(sample_json)
        assert df.shape == (2, 4)

    def test_nested_record_path(self, nested_json):
        df = load_json(nested_json, record_path=["results"])
        assert df.shape == (2, 2)
        assert "score" in df.columns

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_json("/no/such/file.json")


class TestLoadJsonFromDict:
    def test_flat_list(self):
        data = [{"a": 1}, {"a": 2}]
        df = load_json_from_dict(data)
        assert df.shape == (2, 1)

    def test_nested_record_path(self):
        data = {"items": [{"x": 10}, {"x": 20}]}
        df = load_json_from_dict(data, record_path=["items"])
        assert len(df) == 2

    def test_columns_present(self):
        data = [{"id": 1, "name": "Test"}]
        df = load_json_from_dict(data)
        assert "id" in df.columns and "name" in df.columns
