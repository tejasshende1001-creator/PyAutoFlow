"""
utils/config.py
---------------
Configuration management for PyAutoFlow.
Loads settings from environment variables and a JSON config file with
sensible defaults, keeping all tuneable parameters in one place.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """
    Central configuration container for the PyAutoFlow pipeline.

    Attributes
    ----------
    input_dir : str
        Default directory for raw input files.
    output_dir : str
        Default directory for generated reports.
    log_dir : str
        Directory where log files are stored.
    api_base_url : str
        Base URL for the REST API data source.
    api_timeout : int
        HTTP request timeout in seconds.
    api_key : Optional[str]
        Optional API key loaded from the environment.
    report_formats : list[str]
        Output report formats to generate ('csv', 'json', 'txt').
    chunk_size : int
        Number of rows per chunk for large-file streaming.
    decimal_places : int
        Rounding precision for numerical aggregations.
    """

    input_dir: str = "data"
    output_dir: str = "output"
    log_dir: str = "logs"
    api_base_url: str = "https://jsonplaceholder.typicode.com"
    api_timeout: int = 30
    api_key: Optional[str] = None
    report_formats: list = field(default_factory=lambda: ["csv", "json", "txt"])
    chunk_size: int = 10_000
    decimal_places: int = 4

    @classmethod
    def from_file(cls, config_path: str = "config.json") -> "Config":
        """
        Load configuration from a JSON file, falling back to defaults for
        any missing keys.

        Parameters
        ----------
        config_path : str
            Path to the JSON configuration file.

        Returns
        -------
        Config
            Populated Config instance.

        Examples
        --------
        >>> cfg = Config.from_file("config.json")
        >>> print(cfg.api_base_url)
        """
        instance = cls()
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

        # Environment variable overrides (highest priority)
        instance.api_key = os.getenv("PYAUTOFLOW_API_KEY", instance.api_key)
        instance.api_base_url = os.getenv("PYAUTOFLOW_API_URL", instance.api_base_url)

        return instance

    def to_dict(self) -> dict:
        """Serialize configuration to a plain dictionary."""
        return {
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
            "log_dir": self.log_dir,
            "api_base_url": self.api_base_url,
            "api_timeout": self.api_timeout,
            "report_formats": self.report_formats,
            "chunk_size": self.chunk_size,
            "decimal_places": self.decimal_places,
        }
