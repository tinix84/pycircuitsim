"""Core histogram binning for mission-profile to operating-point conversion."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .weighted_op_table import WeightedOPTable


def mission_profile_to_histogram(
    time_series_df: pd.DataFrame,
    columns: list[str],
    n_bins: int | list[int] = 10,
    method: str = "equal_width",
    bin_edges: Optional[dict[str, np.ndarray]] = None,
) -> WeightedOPTable:
    """Convert a time-domain DataFrame into a weighted operating-point table.

    Parameters
    ----------
    time_series_df : pd.DataFrame
        Time-domain waveform data.  Each row is one time step.
    columns : list[str]
        Column names to bin (e.g. ``["V", "I"]``).
    n_bins : int or list[int]
        Number of bins per dimension. A scalar is broadcast to all dims.
    method : ``'equal_width'`` (default) or ``'equal_count'``
        Binning strategy.
    bin_edges : dict mapping column name → 1-D array of edges, optional
        If given, overrides *n_bins* / *method* for that column.

    Returns
    -------
    WeightedOPTable
    """
    # ---- validation ----
    if time_series_df.empty:
        raise ValueError("time_series_df must not be empty")
    missing = [c for c in columns if c not in time_series_df.columns]
    if missing:
        raise ValueError(f"Columns not found in DataFrame: {missing}")
    if isinstance(n_bins, int):
        n_bins_list = [n_bins] * len(columns)
    else:
        if len(n_bins) != len(columns):
            raise ValueError("Length of n_bins must match number of columns")
        n_bins_list = list(n_bins)

    sample = np.column_stack([time_series_df[c].to_numpy(dtype=float) for c in columns])

    # Drop rows with NaN
    mask = ~np.isnan(sample).any(axis=1)
    sample = sample[mask]
    if sample.shape[0] == 0:
        raise ValueError("All rows are NaN after filtering")

    # ---- build edges per dimension ----
    edges_list: list[np.ndarray] = []
    for i, col in enumerate(columns):
        if bin_edges and col in bin_edges:
            edges_list.append(np.asarray(bin_edges[col], dtype=float))
        elif method == "equal_width":
            lo, hi = sample[:, i].min(), sample[:, i].max()
            if lo == hi:
                lo -= 0.5
                hi += 0.5
            edges_list.append(np.linspace(lo, hi, n_bins_list[i] + 1))
        elif method == "equal_count":
            quantiles = np.linspace(0, 100, n_bins_list[i] + 1)
            edges = np.unique(np.percentile(sample[:, i], quantiles))
            # Fallback: if data is constant/near-constant, unique collapses to <2 edges
            if len(edges) < 2:
                lo = edges[0] - 0.5
                hi = edges[0] + 0.5
                edges = np.linspace(lo, hi, n_bins_list[i] + 1)
            edges_list.append(edges)
        else:
            raise ValueError(f"Unknown method: {method!r}")

    # ---- N-dimensional histogram ----
    counts, _ = np.histogramdd(sample, bins=edges_list)

    # ---- flatten to table ----
    centres = [0.5 * (e[:-1] + e[1:]) for e in edges_list]
    grid = np.meshgrid(*centres, indexing="ij")
    flat = {col: g.ravel() for col, g in zip(columns, grid)}
    flat_counts = counts.ravel()

    df = pd.DataFrame(flat)
    df["count"] = flat_counts.astype(int)

    # Drop zero-count bins
    df = df[df["count"] > 0].reset_index(drop=True)

    total = df["count"].sum()
    df["weight_pct"] = df["count"] / total * 100.0

    return WeightedOPTable(
        data=df,
        dimensions=list(columns),
        n_bins=n_bins,
        method=method,
    )
