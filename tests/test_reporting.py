"""
tests/test_reporting.py
------------------------
Unit tests for the PyAutoFlow reporting layer.
Tests cover CSV/JSON/TXT output, directory creation, and multi-format generation.
"""

import json
import os
import pytest
import pandas as pd

from pyautoflow.reporting.report_generator import (
    save_csv,
    save_json,
    save_txt_summary,
    generate_reports,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "region":  ["North", "South", "East"],
        "revenue": [1500.0, 2300.5, 3200.0],
        "units":   [10, 25, 40],
    })


@pytest.fixture
def pipeline_results(sample_df) -> dict:
    return {
        "clean":      sample_df,
        "summary":    sample_df.describe(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# save_csv
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveCsv:
    def test_file_created(self, tmp_path, sample_df):
        fp = str(tmp_path / "report.csv")
        save_csv(sample_df, fp)
        assert os.path.exists(fp)

    def test_returns_absolute_path(self, tmp_path, sample_df):
        fp = str(tmp_path / "report.csv")
        result = save_csv(sample_df, fp)
        assert os.path.isabs(result)

    def test_content_correct(self, tmp_path, sample_df):
        fp = str(tmp_path / "data.csv")
        save_csv(sample_df, fp, index=False)
        loaded = pd.read_csv(fp)
        assert loaded.shape == sample_df.shape


# ─────────────────────────────────────────────────────────────────────────────
# save_json
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveJson:
    def test_file_created(self, tmp_path, sample_df):
        fp = str(tmp_path / "report.json")
        save_json(sample_df, fp)
        assert os.path.exists(fp)

    def test_valid_json(self, tmp_path, sample_df):
        fp = str(tmp_path / "report.json")
        save_json(sample_df, fp)
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == len(sample_df)

    def test_column_present(self, tmp_path, sample_df):
        fp = str(tmp_path / "report.json")
        save_json(sample_df, fp)
        with open(fp, "r") as f:
            records = json.load(f)
        assert "region" in records[0]


# ─────────────────────────────────────────────────────────────────────────────
# save_txt_summary
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveTxtSummary:
    def test_file_created(self, tmp_path, pipeline_results):
        fp = str(tmp_path / "summary.txt")
        save_txt_summary(pipeline_results, fp)
        assert os.path.exists(fp)

    def test_contains_stage_names(self, tmp_path, pipeline_results):
        fp = str(tmp_path / "summary.txt")
        save_txt_summary(pipeline_results, fp)
        content = open(fp, "r", encoding="utf-8").read()
        assert "CLEAN" in content
        assert "SUMMARY" in content

    def test_custom_title(self, tmp_path, pipeline_results):
        fp = str(tmp_path / "custom.txt")
        save_txt_summary(pipeline_results, fp, title="My Custom Report")
        content = open(fp, encoding="utf-8").read()
        assert "My Custom Report" in content


# ─────────────────────────────────────────────────────────────────────────────
# generate_reports
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateReports:
    def test_creates_output_dir(self, tmp_path, pipeline_results):
        out = str(tmp_path / "reports")
        generate_reports(pipeline_results, output_dir=out, formats=["csv"])
        assert os.path.isdir(out)

    def test_csv_files_created(self, tmp_path, pipeline_results):
        out = str(tmp_path / "out")
        result = generate_reports(pipeline_results, output_dir=out, formats=["csv"])
        assert len(result["csv"]) == 2  # one per result key

    def test_json_files_created(self, tmp_path, pipeline_results):
        out = str(tmp_path / "out")
        result = generate_reports(pipeline_results, output_dir=out, formats=["json"])
        assert len(result["json"]) >= 1

    def test_txt_file_created(self, tmp_path, pipeline_results):
        out = str(tmp_path / "out")
        result = generate_reports(pipeline_results, output_dir=out, formats=["txt"])
        assert len(result["txt"]) == 1

    def test_all_formats(self, tmp_path, pipeline_results):
        out = str(tmp_path / "all")
        result = generate_reports(pipeline_results, output_dir=out, formats=["csv", "json", "txt"])
        assert result["csv"] and result["json"] and result["txt"]

    def test_custom_label_in_filename(self, tmp_path, pipeline_results):
        out = str(tmp_path / "labeled")
        generate_reports(pipeline_results, output_dir=out, formats=["csv"], run_label="TEST_RUN")
        files = os.listdir(out)
        assert any("TEST_RUN" in f for f in files)

    def test_empty_df_skipped(self, tmp_path):
        results = {"empty": pd.DataFrame()}
        out = str(tmp_path / "empty_test")
        written = generate_reports(results, output_dir=out, formats=["csv"])
        assert written["csv"] == []
