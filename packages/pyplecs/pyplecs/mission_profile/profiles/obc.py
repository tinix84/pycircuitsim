"""On-Board Charger (OBC) profile generator."""

from __future__ import annotations

import numpy as np


def obc_profile(
    soc: np.ndarray,
    charge_power_w: float = 11_000.0,
    v_bat_min: float = 300.0,
    v_bat_max: float = 420.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate V_bat and I_bat arrays for an OBC charging profile.

    Assumes constant-power charging with a linear V_bat(SoC) mapping.

    Parameters
    ----------
    soc : array-like
        State of charge, values in [0, 1].
    charge_power_w : float
        Charge power [W] (default 11 kW).
    v_bat_min, v_bat_max : float
        Battery voltage at SoC=0 and SoC=1 [V].

    Returns
    -------
    V_bat, I_bat : np.ndarray, np.ndarray
    """
    soc = np.asarray(soc, dtype=float)
    if np.any(soc < 0) or np.any(soc > 1):
        raise ValueError("SoC values must be in [0, 1]")

    V_bat = v_bat_min + (v_bat_max - v_bat_min) * soc
    I_bat = charge_power_w / V_bat

    return V_bat, I_bat
