"""
Satellite-specific feature contracts, cadence settings, and baseline filters.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BaselineFilter:
    field_name: str
    operator: str
    threshold: float

    def mask(self, df: pd.DataFrame) -> pd.Series:
        if self.field_name not in df.columns:
            return pd.Series(False, index=df.index, dtype=bool)

        series = df[self.field_name]
        if self.operator == "gt":
            return series > self.threshold
        if self.operator == "lt":
            return series < self.threshold
        if self.operator == "abs_gt":
            return series.abs() > self.threshold
        raise ValueError(f"Unsupported baseline filter operator: {self.operator}")

    def describe(self) -> str:
        if self.operator == "gt":
            return f"{self.field_name} > {self.threshold}"
        if self.operator == "lt":
            return f"{self.field_name} < {self.threshold}"
        if self.operator == "abs_gt":
            return f"|{self.field_name}| > {self.threshold}"
        return f"{self.field_name} {self.operator} {self.threshold}"


@dataclass(frozen=True)
class FeatureContract:
    version: int
    feature_names: tuple[str, ...]
    diagnosis_feature_names: tuple[str, ...]


@dataclass(frozen=True)
class SatelliteProfile:
    norad_id: int
    name: str
    feature_contract: FeatureContract
    pass_gap_seconds: float
    cadence_tolerance_ratio: float
    cadence_min_tolerance_seconds: float
    rolling_window: int = 3
    baseline_filters: tuple[BaselineFilter, ...] = ()


UWE4_PROFILE = SatelliteProfile(
    norad_id=43880,
    name="UWE-4",
    feature_contract=FeatureContract(
        version=3,
        feature_names=(
            "batt_voltage",
            "batt_current",
            "temp_batt_a",
            "temp_batt_b",
            "temp_panel_z",
        ),
        diagnosis_feature_names=(
            "batt_voltage",
            "batt_current",
            "temp_batt_a",
            "temp_batt_b",
        ),
    ),
    pass_gap_seconds=120.0,
    cadence_tolerance_ratio=0.5,
    cadence_min_tolerance_seconds=5.0,
    rolling_window=3,
    baseline_filters=(
        BaselineFilter("batt_voltage", "gt", 5.0),
        BaselineFilter("batt_current", "abs_gt", 1.0),
    ),
)


_SATELLITE_PROFILES = {
    UWE4_PROFILE.norad_id: UWE4_PROFILE,
}

DEFAULT_PROFILE = UWE4_PROFILE


def get_satellite_profile(norad_id: int | str) -> SatelliteProfile:
    sat_id = int(norad_id)
    if sat_id not in _SATELLITE_PROFILES:
        raise KeyError(f"No satellite profile configured for NORAD {sat_id}")
    return _SATELLITE_PROFILES[sat_id]


def build_baseline_mask(df: pd.DataFrame, profile: SatelliteProfile) -> pd.Series:
    if df.empty:
        return pd.Series(False, index=df.index, dtype=bool)

    mask = pd.Series(False, index=df.index, dtype=bool)
    for baseline_filter in profile.baseline_filters:
        mask |= baseline_filter.mask(df)
    return mask


def feature_completeness_mask(
    df: pd.DataFrame,
    feature_names: list[str] | tuple[str, ...],
) -> pd.Series:
    required = list(feature_names)
    missing_columns = [name for name in required if name not in df.columns]
    if missing_columns:
        raise ValueError(
            "Missing required feature columns: " + ", ".join(sorted(missing_columns))
        )
    return df[required].notna().all(axis=1)
