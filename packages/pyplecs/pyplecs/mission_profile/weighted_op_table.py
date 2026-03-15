"""Weighted operating-point table dataclass."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class WeightedOPTable:
    """A table of operating points with associated weights.

    Each row represents a bin centre for one or more electrical dimensions
    (e.g. V, I) together with a ``weight_pct`` column that sums to 100.
    If both ``V`` and ``I`` columns are present, a ``P`` column is
    auto-computed as their product.
    """

    data: pd.DataFrame = field(repr=False)
    dimensions: list[str] = field(default_factory=list)
    n_bins: int | list[int] = 10
    method: str = "equal_width"

    def __post_init__(self) -> None:
        if "weight_pct" not in self.data.columns:
            raise ValueError("DataFrame must contain a 'weight_pct' column")
        # Auto-compute power if V and I are present but P is not
        if "V" in self.data.columns and "I" in self.data.columns and "P" not in self.data.columns:
            self.data = self.data.copy()
            self.data["P"] = self.data["V"] * self.data["I"]

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def to_csv(self, path: Optional[str] = None) -> Optional[str]:
        """Write to CSV file or return CSV string."""
        if path is not None:
            self.data.to_csv(path, index=False)
            return None
        return self.data.to_csv(index=False)

    def to_dataframe(self) -> pd.DataFrame:
        """Return a copy of the underlying DataFrame."""
        return self.data.copy()

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def plot(self, ax=None, kind: str = "auto", **kwargs):
        """Bar chart (1-D) or heatmap (2-D) of weight distribution.

        Parameters
        ----------
        ax : matplotlib Axes, optional
        kind : ``'bar'``, ``'heatmap'``, or ``'auto'`` (default)
        **kwargs : forwarded to the underlying matplotlib call
        """
        import matplotlib.pyplot as plt

        if ax is None:
            _, ax = plt.subplots()

        dims = [c for c in self.data.columns if c not in ("weight_pct", "P", "count")]

        if kind == "auto":
            kind = "heatmap" if len(dims) >= 2 else "bar"

        if kind == "bar":
            labels = self.data[dims].astype(str).agg(" / ".join, axis=1)
            ax.bar(range(len(labels)), self.data["weight_pct"], **kwargs)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
            ax.set_ylabel("Weight [%]")
            ax.set_title("Operating-Point Weight Distribution")
        elif kind == "heatmap":
            pivot = self.data.pivot_table(
                index=dims[1], columns=dims[0], values="weight_pct", aggfunc="sum", fill_value=0.0
            )
            im = ax.imshow(pivot.values, aspect="auto", origin="lower", **kwargs)
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels([f"{v:.1f}" for v in pivot.columns], rotation=45, fontsize=7)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels([f"{v:.1f}" for v in pivot.index], fontsize=7)
            ax.set_xlabel(dims[0])
            ax.set_ylabel(dims[1])
            ax.set_title("Operating-Point Heatmap [% weight]")
            plt.colorbar(im, ax=ax, label="Weight [%]")
        else:
            raise ValueError(f"Unknown plot kind: {kind!r}")

        return ax

    # ------------------------------------------------------------------
    # Text summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable summary string."""
        buf = io.StringIO()
        buf.write(f"WeightedOPTable  dims={self.dimensions}  "
                  f"bins={self.n_bins}  method={self.method}\n")
        buf.write(f"  {len(self.data)} operating points, "
                  f"weight range {self.data['weight_pct'].min():.2f}–"
                  f"{self.data['weight_pct'].max():.2f} %\n")
        if "P" in self.data.columns:
            buf.write(f"  Power range: {self.data['P'].min():.1f} – "
                      f"{self.data['P'].max():.1f} W\n")
        buf.write(self.data.to_string(index=False))
        return buf.getvalue()

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return (f"WeightedOPTable(n_ops={len(self.data)}, "
                f"dims={self.dimensions}, method={self.method!r})")
