"""Tests for pyplecs.mission_profile module."""

import numpy as np
import pandas as pd
import pytest

from pyplecs.mission_profile import (
    MotorParams,
    PVPanelParams,
    VehicleParams,
    WeightedOPTable,
    load_wltp,
    mission_profile_to_histogram,
    obc_profile,
    pv_mppt,
    wltp_to_electrical,
)


# ── WeightedOPTable ─────────────────────────────────────────────────

class TestWeightedOPTable:
    def test_basic_creation(self):
        df = pd.DataFrame({"V": [10, 20], "I": [1, 2], "weight_pct": [60.0, 40.0]})
        tbl = WeightedOPTable(data=df, dimensions=["V", "I"])
        assert len(tbl) == 2
        assert "P" in tbl.data.columns  # auto-computed
        assert tbl.data["P"].tolist() == [10.0, 40.0]

    def test_missing_weight_raises(self):
        df = pd.DataFrame({"V": [1], "I": [2]})
        with pytest.raises(ValueError, match="weight_pct"):
            WeightedOPTable(data=df)

    def test_to_csv_string(self):
        df = pd.DataFrame({"V": [10], "weight_pct": [100.0]})
        tbl = WeightedOPTable(data=df, dimensions=["V"])
        csv = tbl.to_csv()
        assert "V" in csv
        assert "100.0" in csv

    def test_to_csv_file(self, tmp_path):
        df = pd.DataFrame({"V": [10, 20], "weight_pct": [50.0, 50.0]})
        tbl = WeightedOPTable(data=df, dimensions=["V"])
        path = str(tmp_path / "out.csv")
        tbl.to_csv(path)
        loaded = pd.read_csv(path)
        assert len(loaded) == 2

    def test_to_dataframe_is_copy(self):
        df = pd.DataFrame({"V": [10], "weight_pct": [100.0]})
        tbl = WeightedOPTable(data=df, dimensions=["V"])
        df2 = tbl.to_dataframe()
        df2["V"] = 999
        assert tbl.data["V"].iloc[0] == 10

    def test_summary(self):
        df = pd.DataFrame({"V": [10, 20], "I": [1, 2], "weight_pct": [60.0, 40.0]})
        tbl = WeightedOPTable(data=df, dimensions=["V", "I"])
        s = tbl.summary()
        assert "WeightedOPTable" in s
        assert "Power range" in s

    def test_repr(self):
        df = pd.DataFrame({"V": [10], "weight_pct": [100.0]})
        tbl = WeightedOPTable(data=df, dimensions=["V"])
        assert "n_ops=1" in repr(tbl)


# ── mission_profile_to_histogram ─────────────────────────────────────

class TestHistogram:
    def _make_df(self, n=1000):
        rng = np.random.default_rng(0)
        return pd.DataFrame({
            "V": rng.uniform(300, 420, n),
            "I": rng.uniform(0, 30, n),
        })

    def test_1d_equal_width(self):
        df = self._make_df()
        tbl = mission_profile_to_histogram(df, columns=["V"], n_bins=5)
        assert len(tbl) <= 5
        assert abs(tbl.data["weight_pct"].sum() - 100.0) < 1e-9

    def test_2d_equal_width(self):
        df = self._make_df()
        tbl = mission_profile_to_histogram(df, columns=["V", "I"], n_bins=4)
        assert abs(tbl.data["weight_pct"].sum() - 100.0) < 1e-9
        assert "V" in tbl.data.columns
        assert "I" in tbl.data.columns
        assert "count" in tbl.data.columns

    def test_equal_count_method(self):
        df = self._make_df()
        tbl = mission_profile_to_histogram(df, columns=["V"], n_bins=5, method="equal_count")
        assert len(tbl) > 0
        assert abs(tbl.data["weight_pct"].sum() - 100.0) < 1e-9

    def test_custom_bin_edges(self):
        df = self._make_df()
        edges = {"V": np.array([300, 350, 400, 420])}
        tbl = mission_profile_to_histogram(df, columns=["V"], bin_edges=edges)
        assert len(tbl) <= 3

    def test_per_dim_n_bins(self):
        df = self._make_df()
        tbl = mission_profile_to_histogram(df, columns=["V", "I"], n_bins=[3, 5])
        assert len(tbl) <= 15

    def test_empty_df_raises(self):
        with pytest.raises(ValueError, match="empty"):
            mission_profile_to_histogram(pd.DataFrame(), columns=["V"])

    def test_missing_column_raises(self):
        df = pd.DataFrame({"V": [1, 2, 3]})
        with pytest.raises(ValueError, match="not found"):
            mission_profile_to_histogram(df, columns=["V", "X"])

    def test_bad_method_raises(self):
        df = pd.DataFrame({"V": [1, 2, 3]})
        with pytest.raises(ValueError, match="Unknown method"):
            mission_profile_to_histogram(df, columns=["V"], method="magic")

    def test_nbins_length_mismatch(self):
        df = pd.DataFrame({"V": [1, 2], "I": [3, 4]})
        with pytest.raises(ValueError, match="n_bins"):
            mission_profile_to_histogram(df, columns=["V", "I"], n_bins=[3])

    def test_all_nan_raises(self):
        df = pd.DataFrame({"V": [np.nan, np.nan]})
        with pytest.raises(ValueError, match="NaN"):
            mission_profile_to_histogram(df, columns=["V"])

    def test_constant_column(self):
        df = pd.DataFrame({"V": [400.0] * 100})
        tbl = mission_profile_to_histogram(df, columns=["V"], n_bins=5)
        assert len(tbl) >= 1
        assert abs(tbl.data["weight_pct"].sum() - 100.0) < 1e-9


# ── PV MPPT ──────────────────────────────────────────────────────────

class TestPVMPPT:
    def test_stc_conditions(self):
        params = PVPanelParams()
        V, I = pv_mppt(np.array([1000.0]), np.array([25.0]), params)
        # Simplified model: P_mpp should be close to V_mp * I_mp
        P_expected = params.V_mp * params.I_mp
        assert V[0] * I[0] == pytest.approx(P_expected, rel=0.05)
        assert V[0] == pytest.approx(params.V_mp, rel=0.15)

    def test_zero_irradiance(self):
        V, I = pv_mppt(np.array([0.0]), np.array([25.0]))
        assert V[0] >= 0
        assert I[0] == pytest.approx(0.0, abs=0.01)

    def test_array_input(self):
        G = np.linspace(100, 1000, 50)
        T = np.full(50, 25.0)
        V, I = pv_mppt(G, T)
        assert V.shape == (50,)
        # Higher irradiance → higher current
        assert I[-1] > I[0]

    def test_temperature_effect_on_voltage(self):
        G = np.array([1000.0, 1000.0])
        T = np.array([25.0, 60.0])
        V, I = pv_mppt(G, T)
        assert V[1] < V[0]  # Higher temp → lower voltage

    def test_custom_params(self):
        params = PVPanelParams(I_sc=5.0, V_oc=24.0, I_mp=4.5, V_mp=20.0)
        V, I = pv_mppt(np.array([1000.0]), np.array([25.0]), params)
        P_expected = params.V_mp * params.I_mp
        assert V[0] * I[0] == pytest.approx(P_expected, rel=0.05)


# ── OBC Profile ──────────────────────────────────────────────────────

class TestOBCProfile:
    def test_basic(self):
        soc = np.linspace(0.1, 1.0, 50)
        V, I = obc_profile(soc)
        assert V.shape == (50,)
        assert I.shape == (50,)
        assert np.all(V >= 300)
        assert np.all(V <= 420)

    def test_constant_power(self):
        soc = np.linspace(0.1, 0.9, 10)
        V, I = obc_profile(soc, charge_power_w=7_000)
        P = V * I
        np.testing.assert_allclose(P, 7_000, rtol=1e-10)

    def test_invalid_soc_raises(self):
        with pytest.raises(ValueError, match="SoC"):
            obc_profile(np.array([-0.1, 0.5]))
        with pytest.raises(ValueError, match="SoC"):
            obc_profile(np.array([0.5, 1.1]))


# ── WLTP ─────────────────────────────────────────────────────────────

class TestWLTP:
    def test_load_class3(self):
        df = load_wltp(3)
        assert "time_s" in df.columns
        assert "speed_kmh" in df.columns
        assert len(df) == 1800

    def test_load_class1(self):
        df = load_wltp(1)
        assert len(df) == 589

    def test_load_class2(self):
        df = load_wltp(2)
        assert len(df) == 1022

    def test_invalid_class_raises(self):
        with pytest.raises(ValueError):
            load_wltp(4)

    def test_wltp_to_electrical(self):
        result = wltp_to_electrical(wltp_class=3)
        assert "V" in result.columns
        assert "I" in result.columns
        assert "P_mech" in result.columns
        assert len(result) == 1800

    def test_custom_vehicle_params(self):
        result = wltp_to_electrical(
            wltp_class=1,
            vehicle=VehicleParams(mass=2000),
            motor=MotorParams(V_dc=800),
        )
        assert np.all(result["V"] == 800.0)


# ── End-to-end: profile → histogram ─────────────────────────────────

class TestEndToEnd:
    def test_pv_to_histogram(self):
        G = np.linspace(100, 1000, 200)
        T = np.full(200, 30.0)
        V, I = pv_mppt(G, T)
        df = pd.DataFrame({"V": V, "I": I})
        tbl = mission_profile_to_histogram(df, columns=["V", "I"], n_bins=5)
        assert abs(tbl.data["weight_pct"].sum() - 100.0) < 1e-9
        assert "P" in tbl.data.columns

    def test_obc_to_histogram(self):
        soc = np.linspace(0.1, 1.0, 100)
        V, I = obc_profile(soc)
        df = pd.DataFrame({"V": V, "I": I})
        tbl = mission_profile_to_histogram(df, columns=["V", "I"], n_bins=4)
        assert len(tbl) > 0

    def test_wltp_to_histogram(self):
        elec = wltp_to_electrical(wltp_class=1)
        tbl = mission_profile_to_histogram(elec, columns=["V", "I"], n_bins=6)
        assert abs(tbl.data["weight_pct"].sum() - 100.0) < 1e-9
