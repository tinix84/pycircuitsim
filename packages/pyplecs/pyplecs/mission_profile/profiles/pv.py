"""PV MPPT operating-point generator."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PVPanelParams:
    """STC parameters for a PV panel.

    Defaults approximate a generic 400 W mono-Si module.
    """

    I_sc: float = 10.0       # Short-circuit current [A]
    V_oc: float = 48.0       # Open-circuit voltage [V]
    I_mp: float = 9.5        # MPP current [A]
    V_mp: float = 42.0       # MPP voltage [V]
    alpha_I: float = 0.05    # Temp coefficient of I_sc [%/°C]
    beta_V: float = -0.30    # Temp coefficient of V_oc [%/°C]


def pv_mppt(
    irradiance: np.ndarray,
    temperature: np.ndarray,
    params: PVPanelParams | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate MPP voltage and current for given irradiance and temperature.

    Uses a simplified single-diode fill-factor approach: scales I_sc
    linearly with irradiance ratio and temperature, adjusts V_oc with
    temperature, then applies the STC fill factor.

    Parameters
    ----------
    irradiance : array-like
        In-plane irradiance [W/m²].
    temperature : array-like
        Cell temperature [°C].
    params : PVPanelParams, optional
        Panel datasheet values.  Defaults to a generic 400 W module.

    Returns
    -------
    V_mpp, I_mpp : np.ndarray, np.ndarray
    """
    if params is None:
        params = PVPanelParams()

    G = np.asarray(irradiance, dtype=float)
    T = np.asarray(temperature, dtype=float)
    dT = T - 25.0  # deviation from STC

    # Scale short-circuit current
    I_sc_eff = params.I_sc * (G / 1000.0) * (1.0 + params.alpha_I / 100.0 * dT)

    # Scale open-circuit voltage
    V_oc_eff = params.V_oc * (1.0 + params.beta_V / 100.0 * dT)
    # Logarithmic correction for low irradiance
    G_safe = np.clip(G, 1.0, None)
    V_oc_eff = V_oc_eff + 0.0257 * np.log(G_safe / 1000.0)
    V_oc_eff = np.clip(V_oc_eff, 0.0, None)

    # Fill factor at STC
    ff = (params.V_mp * params.I_mp) / (params.V_oc * params.I_sc)

    # Approximate MPP as FF * Voc * Isc
    P_mp = ff * V_oc_eff * I_sc_eff
    V_mpp = ff * V_oc_eff
    I_mpp = np.where(V_mpp > 0, P_mp / V_mpp, 0.0)

    return V_mpp, I_mpp
