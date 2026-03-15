"""Mission-profile to weighted operating-point converter.

Public API
----------
- ``mission_profile_to_histogram`` – core binning function
- ``WeightedOPTable`` – result dataclass
- ``pv_mppt`` / ``PVPanelParams`` – PV profile helpers
- ``obc_profile`` – on-board charger profile
- ``wltp_to_electrical`` / ``load_wltp`` – WLTP drive-cycle conversion
- ``VehicleParams`` / ``MotorParams`` – vehicle/motor parameter dataclasses
"""

from .histogram import mission_profile_to_histogram
from .profiles import (
    MotorParams,
    PVPanelParams,
    VehicleParams,
    load_wltp,
    obc_profile,
    pv_mppt,
    wltp_to_electrical,
)
from .weighted_op_table import WeightedOPTable

__all__ = [
    "WeightedOPTable",
    "mission_profile_to_histogram",
    "pv_mppt",
    "PVPanelParams",
    "obc_profile",
    "wltp_to_electrical",
    "load_wltp",
    "VehicleParams",
    "MotorParams",
]
