from typing import Optional, Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Integer, Identity
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class RawFrame(SQLModel, table=True):
    __tablename__ = "raw_frames"
    id: Optional[int] = Field(default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True))
    timestamp: datetime = Field(primary_key=True)
    norad_id: int
    station_id: Optional[str] = None
    raw_frame: str
    snr: Optional[float] = None

class TelemetryFrame(SQLModel, table=True):
    __tablename__ = "telemetry_frames"
    id: Optional[int] = Field(default=None, sa_column=Column(Integer, Identity(always=True), primary_key=True))
    timestamp: datetime = Field(primary_key=True)
    norad_id: int
    raw_frame_id: Optional[int] = None
    features: Any = Field(default=dict, sa_column=Column(JSONB))
    anomaly_score: Optional[float] = None
    is_anomaly: Optional[bool] = Field(default=False)
    missing_fields: Any = Field(default=list, sa_column=Column(JSONB))
