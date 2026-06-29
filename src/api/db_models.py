from typing import Optional, Any
from sqlmodel import Field, SQLModel, Column, DateTime
from sqlalchemy import Integer, Identity
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from datetime import datetime, timezone
import secrets

class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), index=True, unique=True)
    description: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RawFrame(SQLModel, table=True):
    __tablename__ = "raw_frames"
    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), primary_key=True))
    norad_id: int
    station_id: Optional[str] = None
    raw_frame: str
    snr: Optional[float] = None


class TelemetryRow(SQLModel, table=True):
    __tablename__ = "telemetry_frames"
    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), primary_key=True))
    norad_id: int
    raw_frame_id: Optional[int] = None
    features: Any = Field(default=dict, sa_column=Column(JSONB))
    anomaly_score: Optional[float] = None
    is_anomaly: Optional[bool] = Field(default=False)
    missing_fields: Any = Field(default=list, sa_column=Column(JSONB))
    frame_is_complete: bool = Field(default=True)
    missing_raw_fields: Optional[str] = None
    dropped_packet_suspect: bool = Field(default=False)
    sampling_irregular: bool = Field(default=False)
    pass_id: Optional[int] = None
    pass_duration_sec: Optional[float] = None
    pass_frame_count: Optional[int] = None

class TleRecord(SQLModel, table=True):
    __tablename__ = "tle_records"
    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    norad_id: int = Field(index=True)
    epoch_timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    tle_line1: str
    tle_line2: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(default="api")

class SpaceWeatherRecord(SQLModel, table=True):
    __tablename__ = "space_weather"
    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), unique=True))
    f107_index: float
    kp_index: float
    ap_index: float
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConjunctionRecord(SQLModel, table=True):
    __tablename__ = "conjunctions"
    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    primary_norad_id: int = Field(index=True)
    secondary_norad_id: int
    tca_timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    miss_distance_km: float
    collision_probability: float
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
