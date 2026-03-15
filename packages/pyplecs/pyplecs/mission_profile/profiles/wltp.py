"""WLTP drive-cycle to electrical operating-point converter."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

import numpy as np
import pandas as pd


@dataclass
class VehicleParams:
    """Longitudinal vehicle model parameters."""

    mass: float = 1_500.0          # Vehicle mass [kg]
    Cd: float = 0.28               # Drag coefficient
    A_front: float = 2.2           # Frontal area [m²]
    Cr: float = 0.01               # Rolling-resistance coefficient
    rho_air: float = 1.225         # Air density [kg/m³]


@dataclass
class MotorParams:
    """Simple traction motor/inverter parameters."""

    pole_pairs: int = 4
    gear_ratio: float = 9.73
    wheel_radius: float = 0.317    # [m]
    efficiency: float = 0.92       # motor + inverter
    V_dc: float = 400.0            # DC-link voltage [V]


def load_wltp(wltp_class: int = 3) -> pd.DataFrame:
    """Load a built-in WLTP speed profile.

    Parameters
    ----------
    wltp_class : 1, 2, or 3

    Returns
    -------
    pd.DataFrame with columns ``time_s`` and ``speed_kmh``
    """
    if wltp_class not in (1, 2, 3):
        raise ValueError("wltp_class must be 1, 2, or 3")
    fname = f"wltp_class{wltp_class}.csv"
    data_pkg = resources.files("pyplecs.mission_profile.data")
    csv_path = data_pkg / fname
    return pd.read_csv(csv_path)


def wltp_to_electrical(
    speed_profile: pd.DataFrame | None = None,
    wltp_class: int = 3,
    vehicle: VehicleParams | None = None,
    motor: MotorParams | None = None,
) -> pd.DataFrame:
    """Convert a WLTP speed profile to electrical operating points.

    Parameters
    ----------
    speed_profile : pd.DataFrame, optional
        Must have ``time_s`` and ``speed_kmh`` columns.
        If *None*, loads the built-in profile for *wltp_class*.
    wltp_class : int
        Used when *speed_profile* is None.
    vehicle : VehicleParams, optional
    motor : MotorParams, optional

    Returns
    -------
    pd.DataFrame with columns ``time_s``, ``speed_kmh``, ``V``, ``I``, ``P_mech``
    """
    if speed_profile is None:
        speed_profile = load_wltp(wltp_class)
    if vehicle is None:
        vehicle = VehicleParams()
    if motor is None:
        motor = MotorParams()

    t = speed_profile["time_s"].to_numpy(dtype=float)
    v_kmh = speed_profile["speed_kmh"].to_numpy(dtype=float)
    v_ms = v_kmh / 3.6

    # Acceleration (forward difference, 0 for last sample)
    a = np.zeros_like(v_ms)
    dt = np.diff(t)
    dt_safe = np.where(dt == 0, 1.0, dt)
    a[:-1] = np.diff(v_ms) / dt_safe

    # Road forces
    F_drag = 0.5 * vehicle.rho_air * vehicle.Cd * vehicle.A_front * v_ms**2
    F_roll = vehicle.Cr * vehicle.mass * 9.81 * np.ones_like(v_ms)
    F_accel = vehicle.mass * a
    F_total = F_drag + F_roll + F_accel

    P_mech = F_total * v_ms  # [W]

    # Electrical side (sign-aware efficiency: divide when motoring, multiply when regen)
    P_elec = np.where(P_mech >= 0, P_mech / motor.efficiency, P_mech * motor.efficiency)
    V_dc = np.full_like(P_mech, motor.V_dc)
    I_dc = P_elec / motor.V_dc

    return pd.DataFrame({
        "time_s": t,
        "speed_kmh": v_kmh,
        "V": V_dc,
        "I": I_dc,
        "P_mech": P_mech,
    })
