"""Database models for stock-agent-center."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StockCandidate(Base):
    __tablename__ = "stock_candidates"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(64), index=True, nullable=False)
    score = Column(Float, nullable=True)
    signal = Column(String(128), nullable=True)
    source = Column(String(128), default="manual", nullable=False)
    decision = Column(String(64), nullable=True)
    depth = Column(String(32), nullable=True)
    raw_payload = Column(Text, nullable=True)
    created_time = Column(DateTime, default=datetime.utcnow, nullable=False)


class UziReport(Base):
    __tablename__ = "uzi_reports"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(64), index=True, nullable=False)
    job_id = Column(String(128), index=True, nullable=True)
    depth = Column(String(32), nullable=False)
    report_url = Column(Text, nullable=True)
    status = Column(String(64), default="submitted", nullable=False)
    source = Column(String(128), default="manual", nullable=False)
    raw_response = Column(Text, nullable=True)
    created_time = Column(DateTime, default=datetime.utcnow, nullable=False)
