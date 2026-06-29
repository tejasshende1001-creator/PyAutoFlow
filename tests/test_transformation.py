"""
tests/test_transformation.py
------------------------------
Unit tests for the PyAutoFlow transformation layer.
Tests cover cleaning, aggregation, rolling stats, outlier detection,
and the full run_pipeline entry point.
"""

import numpy as np
import pandas as pd
import pytest

from pyautoflow.transformation.cleaner import (
    drop_duplicates,
    handle_missing,
    standardise_columns,
    cast_dtypes,
    clean_dataframe,
)
from pyautoflow.transformation.aggregator import (
    numeric_summary,
    group_aggregate,
    rolling_stats,
    detect_outliers_iqr,
)
from pyautoflow.transformation.transformer import (
    add_derived_columns,
    filter_rows,
    run_pipeline,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def base_df() -> pd.DataFrame:
    """Reusable sample DataFrame for transformation tests."""
    return pd.DataFrame({
        "id":       [1, 2, 3, 4, 4],        # row 4 is a duplicate
        "region":   ["North", "South", "North", "East", "East"],
        "category": ["A", "B", "A", "B", "B"],
        "revenue":  [1500.0, 2300.5, np.nan, 3200.0, 3200.0],
        "units":    [10, 25, 8, 40, 40],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Cleaner Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDropDuplicates:
    def test_removes_duplicates(self, base_df):
        result = drop_duplicates(base_df)
        assert len(result) == 4

    def test_no_duplicates_unchanged(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = drop_duplicates(df)
        assert len(result) == 3

    def test_subset_dedup(self, base_df):
        result = drop_duplicates(base_df, subset=["region"])
        assert len(result) == 3   # North, South, East


class TestHandleMissing:
    def test_drop_strategy(self, base_df):
        result = handle_missing(base_df, strategy="drop")
        assert result.isna().sum().sum() == 0

    def test_fill_strategy(self, base_df):
        result = handle_missing(base_df, strategy="fill", fill_value=0)
        assert result.isna().sum().sum() == 0
        assert result["revenue"].iloc[2] == 0

    def test_smart_strategy_fills_numeric(self, base_df):
        result = handle_missing(base_df, strategy="smart", numeric_strategy="mean")
        assert result["revenue"].isna().sum() == 0
        # filled value should be approximately the mean of [1500, 2300.5, 3200, 3200]
        expected_fill = np.mean([1500.0, 2300.5, 3200.0, 3200.0])
        assert abs(result["revenue"].iloc[2] - expected_fill) < 0.01


class TestStandardiseColumns:
    def test_lowercase(self):
        df = pd.DataFrame({"Revenue": [1], "UNITS Sold": [2], "First-Name": [3]})
        result = standardise_columns(df)
        # "First-Name" → lowercase + hyphen replaced by underscore → "first_name"
        assert list(result.columns) == ["revenue", "units_sold", "first_name"]

    def test_strips_whitespace(self):
        df = pd.DataFrame({" col ": [1]})
        result = standardise_columns(df)
        assert "col" in result.columns


class TestCastDtypes:
    def test_cast_float(self):
        df = pd.DataFrame({"price": ["1.5", "2.0", "3.7"]})
        result = cast_dtypes(df, {"price": "float64"})
        assert result["price"].dtype == np.float64

    def test_missing_column_skipped(self):
        df = pd.DataFrame({"a": [1]})
        result = cast_dtypes(df, {"nonexistent": "int32"})  # should not raise
        assert "nonexistent" not in result.columns


class TestCleanDataframe:
    def test_returns_dataframe(self, base_df):
        result = clean_dataframe(base_df)
        assert isinstance(result, pd.DataFrame)

    def test_removes_duplicates_and_nulls(self, base_df):
        result = clean_dataframe(base_df)
        assert result.duplicated().sum() == 0
        assert result.isna().sum().sum() == 0

    def test_column_names_standardised(self):
        df = pd.DataFrame({"First Name": ["Alice"], "Last  Name": ["Smith"], "Score": [99]})
        result = clean_dataframe(df)
        assert "first_name" in result.columns


# ─────────────────────────────────────────────────────────────────────────────
# Aggregator Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def clean_df() -> pd.DataFrame:
    return pd.DataFrame({
        "region":   ["North", "South", "North", "East"],
        "category": ["A", "B", "A", "B"],
        "revenue":  [1500.0, 2300.5, 800.0, 3200.0],
        "units":    [10, 25, 8, 40],
    })


class TestNumericSummary:
    def test_returns_dataframe(self, clean_df):
        summary = numeric_summary(clean_df)
        assert isinstance(summary, pd.DataFrame)

    def test_correct_columns(self, clean_df):
        summary = numeric_summary(clean_df)
        assert "mean" in summary.columns and "std" in summary.columns

    def test_mean_correct(self, clean_df):
        summary = numeric_summary(clean_df, columns=["revenue"])
        expected = np.mean([1500.0, 2300.5, 800.0, 3200.0])
        assert abs(summary.loc["revenue", "mean"] - expected) < 0.001

    def test_no_numeric_columns(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        summary = numeric_summary(df)
        assert summary.empty


class TestGroupAggregate:
    def test_returns_correct_groups(self, clean_df):
        result = group_aggregate(clean_df, ["region"], {"revenue": "sum"})
        assert "region" in result.columns
        assert len(result) == 3   # North, South, East

    def test_north_sum(self, clean_df):
        result = group_aggregate(clean_df, ["region"], {"revenue": "sum"})
        north_rev = result.loc[result["region"] == "North", "revenue"].values[0]
        assert abs(north_rev - 2300.0) < 0.01

    def test_missing_column_raises(self, clean_df):
        with pytest.raises(ValueError):
            group_aggregate(clean_df, ["nonexistent"], {"revenue": "sum"})


class TestRollingStats:
    def test_adds_columns(self, clean_df):
        result = rolling_stats(clean_df, "revenue", window=2)
        assert "revenue_rolling_mean" in result.columns
        assert "revenue_rolling_std" in result.columns

    def test_rolling_mean_length(self, clean_df):
        result = rolling_stats(clean_df, "revenue", window=2)
        assert len(result) == len(clean_df)


class TestDetectOutliersIqr:
    def test_adds_outlier_column(self, clean_df):
        result = detect_outliers_iqr(clean_df, "revenue")
        assert "revenue_is_outlier" in result.columns

    def test_correct_dtype(self, clean_df):
        result = detect_outliers_iqr(clean_df, "revenue")
        assert result["revenue_is_outlier"].dtype == bool

    def test_known_outlier_detected(self):
        df = pd.DataFrame({"val": [1.0, 2.0, 2.0, 2.0, 100.0]})
        result = detect_outliers_iqr(df, "val")
        assert result["val_is_outlier"].iloc[-1]   # 100.0 should be flagged


# ─────────────────────────────────────────────────────────────────────────────
# Transformer / Pipeline Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAddDerivedColumns:
    def test_adds_column(self, clean_df):
        result = add_derived_columns(clean_df, {"revenue_units": "revenue + units"})
        assert "revenue_units" in result.columns

    def test_correct_values(self, clean_df):
        result = add_derived_columns(clean_df, {"double": "revenue * 2"})
        assert abs(result["double"].iloc[0] - 3000.0) < 0.01


class TestFilterRows:
    def test_filters_correctly(self, clean_df):
        result = filter_rows(clean_df, ["units > 10"])
        assert all(result["units"] > 10)

    def test_multiple_conditions(self, clean_df):
        result = filter_rows(clean_df, ["units > 5", "revenue > 1000"])
        assert len(result) < len(clean_df)


class TestRunPipeline:
    def test_returns_dict(self, base_df):
        results = run_pipeline(base_df)
        assert isinstance(results, dict)

    def test_clean_key_present(self, base_df):
        results = run_pipeline(base_df)
        assert "clean" in results

    def test_summary_key_present(self, base_df):
        results = run_pipeline(base_df)
        assert "summary" in results

    def test_aggregated_key_present(self, base_df):
        results = run_pipeline(
            base_df,
            group_by=["region"],
            agg_map={"units": "sum"},
        )
        assert "aggregated" in results

    def test_outliers_key_present(self, base_df):
        results = run_pipeline(base_df, outlier_col="units")
        assert "outliers" in results

    def test_pipeline_reduces_row_count(self, base_df):
        # base_df has 1 duplicate + 1 NaN row → expect fewer rows
        results = run_pipeline(base_df, missing_strategy="drop")
        assert len(results["clean"]) < len(base_df)
