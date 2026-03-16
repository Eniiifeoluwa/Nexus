"""
Dataset Loader Tool
───────────────────
Loads datasets from multiple sources:
  - Local files (CSV, JSON, Parquet, Excel)
  - URLs (direct download)
  - Built-in synthetic generators (for demo / testing)

Returns a pandas DataFrame + metadata dict.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger(__name__)


class DatasetLoaderTool:
    """Multi-source dataset loader returning pandas DataFrames."""

    TIMEOUT = 30  # seconds for HTTP downloads

    def load(
        self,
        source: str,
        file_format: str | None = None,
    ) -> dict[str, Any]:
        """
        Load a dataset.

        Parameters
        ----------
        source:
            Path, URL, or synthetic generator name
            (e.g. "synthetic:sales", "synthetic:iris", "synthetic:timeseries")
        file_format:
            Force a specific parser ("csv", "json", "parquet", "excel").
            If None, inferred from the source extension.

        Returns
        -------
        {
            "dataframe": pd.DataFrame,
            "shape": (rows, cols),
            "columns": [...],
            "dtypes": {...},
            "source": str,
        }
        """
        if source.startswith("synthetic:"):
            df = self._generate_synthetic(source.split(":", 1)[1])
        elif source.startswith("http://") or source.startswith("https://"):
            df = self._load_url(source, file_format)
        else:
            df = self._load_file(Path(source), file_format)

        return {
            "dataframe": df,
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "source": source,
        }

    # ── Loaders ────────────────────────────────────────────────────────────────

    def _load_file(self, path: Path, fmt: str | None) -> pd.DataFrame:
        fmt = fmt or path.suffix.lstrip(".")
        loaders = {
            "csv": pd.read_csv,
            "json": pd.read_json,
            "parquet": pd.read_parquet,
            "xls": pd.read_excel,
            "xlsx": pd.read_excel,
        }
        loader = loaders.get(fmt.lower())
        if loader is None:
            raise ValueError(f"Unsupported format: {fmt}")
        df = loader(str(path))
        logger.info("Loaded file %s → shape %s", path, df.shape)
        return df

    def _load_url(self, url: str, fmt: str | None) -> pd.DataFrame:
        logger.info("Downloading dataset from %s", url)
        resp = requests.get(url, timeout=self.TIMEOUT)
        resp.raise_for_status()
        ext = Path(url).suffix.lstrip(".") or fmt or "csv"
        return self._load_file(io.BytesIO(resp.content), ext)  # type: ignore[arg-type]

    # ── Synthetic generators ───────────────────────────────────────────────────

    def _generate_synthetic(self, name: str) -> pd.DataFrame:
        rng = np.random.default_rng(42)

        generators = {
            "sales": self._gen_sales,
            "iris": self._gen_iris,
            "timeseries": self._gen_timeseries,
            "ecommerce": self._gen_ecommerce,
        }
        gen = generators.get(name.lower())
        if gen is None:
            logger.warning("Unknown synthetic dataset '%s'; using sales", name)
            gen = self._gen_sales
        df = gen(rng)
        logger.info("Generated synthetic dataset '%s' shape=%s", name, df.shape)
        return df

    @staticmethod
    def _gen_sales(rng: np.random.Generator) -> pd.DataFrame:
        n = 500
        return pd.DataFrame(
            {
                "date": pd.date_range("2023-01-01", periods=n, freq="D"),
                "product": rng.choice(["Widget A", "Widget B", "Gadget C"], n),
                "region": rng.choice(["North", "South", "East", "West"], n),
                "units_sold": rng.integers(1, 200, n),
                "unit_price": rng.uniform(9.99, 99.99, n).round(2),
                "revenue": None,  # computed below
            }
        ).assign(revenue=lambda df: (df.units_sold * df.unit_price).round(2))

    @staticmethod
    def _gen_iris(rng: np.random.Generator) -> pd.DataFrame:
        from sklearn.datasets import load_iris  # type: ignore
        data = load_iris(as_frame=True)
        return data.frame

    @staticmethod
    def _gen_timeseries(rng: np.random.Generator) -> pd.DataFrame:
        n = 365
        dates = pd.date_range("2023-01-01", periods=n)
        value = np.cumsum(rng.normal(0, 1, n)) + 100
        return pd.DataFrame({"date": dates, "value": value.round(3)})

    @staticmethod
    def _gen_ecommerce(rng: np.random.Generator) -> pd.DataFrame:
        n = 1000
        return pd.DataFrame(
            {
                "order_id": range(1, n + 1),
                "customer_age": rng.integers(18, 70, n),
                "category": rng.choice(["Electronics", "Clothing", "Books", "Home"], n),
                "order_value": rng.exponential(50, n).round(2),
                "satisfaction": rng.integers(1, 6, n),
                "returned": rng.choice([True, False], n, p=[0.1, 0.9]),
            }
        )
