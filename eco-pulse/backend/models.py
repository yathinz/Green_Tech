"""
Eco-Pulse V3.0 — SQLAlchemy Models
Defines all 9 database tables as SQLAlchemy ORM models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import DeclarativeBase


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Base(DeclarativeBase):
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 1: inventory_items
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(String, primary_key=True, default=_uuid)
    item_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    expiry_date = Column(String, nullable=True)  # ISO-8601 date
    status = Column(String, nullable=False, default="ACTIVE")
    co2_per_unit_kg = Column(Float, default=0.0)
    confidence_score = Column(Float, nullable=True)
    input_method = Column(String, nullable=False, default="TEXT")
    created_at = Column(String, default=_now_iso)
    updated_at = Column(String, default=_now_iso, onupdate=_now_iso)

    __table_args__ = (
        Index("idx_inventory_status_expiry", "status", "expiry_date"),
        Index("idx_inventory_name_expiry", "item_name", "expiry_date", "status"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 2: pending_human_review
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PendingHumanReview(Base):
    __tablename__ = "pending_human_review"

    id = Column(String, primary_key=True, default=_uuid)
    raw_input = Column(Text, nullable=False)
    llm_response = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    failure_reason = Column(String, nullable=False)
    suggested_item_name = Column(String, nullable=True)
    suggested_quantity = Column(Float, nullable=True)
    reviewed = Column(Integer, default=0)  # 0=pending, 1=approved, 2=rejected
    created_at = Column(String, default=_now_iso)

    __table_args__ = (
        Index("idx_review_status", "reviewed"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 3: inventory_events
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class InventoryEvent(Base):
    __tablename__ = "inventory_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    qty_change = Column(Float, nullable=False)
    day_of_week = Column(Integer, nullable=True)  # 0-6 Mon-Sun
    is_weekend = Column(Integer, nullable=True)  # 0 or 1
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_events_item_timestamp", "item_id", "timestamp"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 4: carbon_impact_db
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CarbonImpact(Base):
    __tablename__ = "carbon_impact_db"

    item_id = Column(String, primary_key=True, default=_uuid)
    item_name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    co2_per_unit_kg = Column(Float, nullable=False)
    avg_shelf_life_days = Column(Integer, nullable=True)
    preferred_partner = Column(String, default="N/A")

    __table_args__ = (
        Index("idx_carbon_item_name", "item_name"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 5: triage_actions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TriageAction(Base):
    __tablename__ = "triage_actions"

    id = Column(String, primary_key=True, default=_uuid)
    item_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    ai_generated = Column(Integer, nullable=False, default=1)
    ai_bypassed = Column(Integer, default=0)
    content = Column(Text, nullable=True)
    created_at = Column(String, default=_now_iso)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 6: audit_log
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, default=_now_iso)
    event_type = Column(String, nullable=False)
    severity = Column(String, default="INFO")
    details = Column(Text, nullable=True)
    input_method = Column(String, nullable=True)
    model_used = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_audit_event_timestamp", "event_type", "timestamp"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 7: forecasts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, nullable=False)
    predicted_runout_date = Column(String, nullable=True)
    days_of_supply = Column(Float, nullable=True)
    daily_burn_rate = Column(Float, nullable=True)
    weekend_multiplier = Column(Float, nullable=True, default=1.0)
    r_squared = Column(Float, nullable=True)
    data_points_used = Column(Integer, nullable=True)
    computed_at = Column(String, default=_now_iso)

    __table_args__ = (
        Index("idx_forecast_item", "item_id"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 8: recipes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RecipeRecord(Base):
    __tablename__ = "recipes"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    ingredients_used = Column(Text, nullable=False)  # JSON array of names
    ingredient_names = Column(Text, nullable=False)  # comma-separated for Grafana
    instructions = Column(Text, nullable=False)
    estimated_servings = Column(Integer, nullable=True)
    co2_saved_kg = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    suggested_price = Column(Float, nullable=True)
    discount_percent = Column(Integer, nullable=True)
    ai_generated = Column(Integer, default=1)
    created_at = Column(String, default=_now_iso)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Table 9: system_config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SystemConfig(Base):
    __tablename__ = "system_config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(String, default=_now_iso)
