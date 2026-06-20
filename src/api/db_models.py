from typing import Optional, Any
from sqlmodel import Field, SQLModel, Column
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
    timestamp: datetime = Field(primary_key=True)
    norad_id: int
    station_id: Optional[str] = None
    raw_frame: str
    snr: Optional[float] = None


class TelemetryRow(SQLModel, table=True):
    __tablename__ = "telemetry_frames"
    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    timestamp: datetime = Field(primary_key=True)
    norad_id: int
    raw_frame_id: Optional[int] = None
    features: Any = Field(default=dict, sa_column=Column(JSONB))
    anomaly_score: Optional[float] = None
    is_anomaly: Optional[bool] = Field(default=False)
    missing_fields: Any = Field(default=list, sa_column=Column(JSONB))
