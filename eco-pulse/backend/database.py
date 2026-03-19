"""
Eco-Pulse V3.0 — Database Layer
Async SQLite engine with WAL mode, session factory, and helper functions.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import (
    AuditLog,
    Base,
    CarbonImpact,
    Forecast,
    InventoryEvent,
    InventoryItem,
    PendingHumanReview,
    RecipeRecord,
    SystemConfig,
    TriageAction,
)

logger = logging.getLogger("ecopulse.database")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Engine & Session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_engine = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def init_db(database_path: str) -> None:
    """
    Initialise the async SQLite engine with WAL mode, create all tables
    and performance indexes.
    """
    global _engine, _session_factory

    url = f"sqlite+aiosqlite:///{database_path}"
    _engine = create_async_engine(url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Set PRAGMAs — WAL mode for concurrent Grafana reads
    async with _engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA busy_timeout=5000;"))

    # ── Migrations for existing databases ──
    async with _engine.begin() as conn:
        # Add discount columns to recipes table (idempotent)
        for col, col_type in [
            ("original_price", "REAL"),
            ("suggested_price", "REAL"),
            ("discount_percent", "INTEGER"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE recipes ADD COLUMN {col} {col_type}"))
            except Exception:
                pass  # Column already exists

    logger.info("Database initialised at %s (WAL mode)", database_path)


async def get_session() -> AsyncSession:
    """Get a new async session."""
    assert _session_factory is not None, "Database not initialised. Call init_db() first."
    return _session_factory()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Generic Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def _execute(query: str, params: Optional[dict] = None) -> list[dict]:
    """Execute a raw SQL query and return results as list of dicts."""
    async with _engine.begin() as conn:
        result = await conn.execute(text(query), params or {})
        try:
            rows = result.fetchall()
            cols = result.keys()
            return [dict(zip(cols, row)) for row in rows]
        except Exception:
            return []


async def _execute_write(query: str, params: Optional[dict] = None) -> None:
    """Execute a raw SQL write query."""
    async with _engine.begin() as conn:
        await conn.execute(text(query), params or {})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Inventory Items
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def insert_inventory_item(
    *,
    item_name: str,
    category: str,
    quantity: float,
    unit: str,
    expiry_date: Optional[str],
    co2_per_unit_kg: float,
    confidence_score: float,
    input_method: str,
    status: str = "ACTIVE",
) -> str:
    """Insert a new inventory item and return its ID."""
    item_id = str(uuid.uuid4())
    now = _now_iso()
    await _execute_write(
        """INSERT INTO inventory_items
           (id, item_name, category, quantity, unit, expiry_date, status,
            co2_per_unit_kg, confidence_score, input_method, created_at, updated_at)
           VALUES (:id, :name, :cat, :qty, :unit, :exp, :status,
                   :co2, :conf, :method, :now, :now)""",
        {
            "id": item_id,
            "name": item_name,
            "cat": category,
            "qty": quantity,
            "unit": unit,
            "exp": expiry_date,
            "status": status,
            "co2": co2_per_unit_kg,
            "conf": confidence_score,
            "method": input_method,
            "now": now,
        },
    )
    return item_id


async def update_inventory_item(
    item_id: str, **fields: Any
) -> None:
    """Update specific fields on an inventory item."""
    fields["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    await _execute_write(
        f"UPDATE inventory_items SET {set_clause} WHERE id = :item_id",
        {**fields, "item_id": item_id},
    )


async def get_item(item_id: str) -> Optional[dict]:
    rows = await _execute(
        "SELECT * FROM inventory_items WHERE id = :id", {"id": item_id}
    )
    return rows[0] if rows else None


async def get_all_active_items() -> list[dict]:
    return await _execute(
        "SELECT * FROM inventory_items WHERE status IN ('ACTIVE', 'EXPIRING_SOON') ORDER BY expiry_date ASC"
    )


async def get_all_items(
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """List items with optional filters."""
    query = "SELECT * FROM inventory_items WHERE 1=1"
    params: dict = {}
    if category:
        query += " AND category = :category"
        params["category"] = category
    if status:
        query += " AND status = :status"
        params["status"] = status
    if search:
        query += " AND item_name LIKE :search"
        params["search"] = f"%{search}%"
    query += " ORDER BY CASE WHEN expiry_date IS NULL THEN 1 ELSE 0 END, expiry_date ASC"
    return await _execute(query, params)


async def search_items(q: str) -> list[dict]:
    return await _execute(
        "SELECT * FROM inventory_items WHERE item_name LIKE :q OR category LIKE :q ORDER BY item_name",
        {"q": f"%{q}%"},
    )


async def delete_item(item_id: str) -> None:
    await _execute_write("DELETE FROM inventory_items WHERE id = :id", {"id": item_id})


async def get_items_expiring_within(days: int) -> list[dict]:
    """Get items expiring within N days of the current (possibly simulated) date."""
    sim_date = await get_config("simulated_date")
    date_ref = sim_date if sim_date else "date('now')"

    if sim_date:
        query = f"""
            SELECT * FROM inventory_items
            WHERE expiry_date IS NOT NULL
              AND status IN ('ACTIVE', 'EXPIRING_SOON')
              AND julianday(expiry_date) - julianday(:ref) <= :days
              AND julianday(expiry_date) - julianday(:ref) >= 0
            ORDER BY expiry_date ASC
        """
        return await _execute(query, {"ref": sim_date, "days": days})
    else:
        query = f"""
            SELECT * FROM inventory_items
            WHERE expiry_date IS NOT NULL
              AND status IN ('ACTIVE', 'EXPIRING_SOON')
              AND julianday(expiry_date) - julianday(date('now')) <= :days
              AND julianday(expiry_date) - julianday(date('now')) >= 0
            ORDER BY expiry_date ASC
        """
        return await _execute(query, {"days": days})


async def get_current_quantity(item_id: str) -> float:
    rows = await _execute(
        "SELECT quantity FROM inventory_items WHERE id = :id", {"id": item_id}
    )
    return rows[0]["quantity"] if rows else 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Pending Human Review
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def insert_pending_review(
    *,
    raw_input: str,
    llm_response: Optional[str],
    confidence_score: Optional[float],
    failure_reason: str,
    suggested_item_name: Optional[str] = None,
    suggested_quantity: Optional[float] = None,
) -> str:
    review_id = str(uuid.uuid4())
    await _execute_write(
        """INSERT INTO pending_human_review
           (id, raw_input, llm_response, confidence_score, failure_reason,
            suggested_item_name, suggested_quantity, reviewed, created_at)
           VALUES (:id, :raw, :llm, :conf, :reason, :name, :qty, 0, :now)""",
        {
            "id": review_id,
            "raw": raw_input,
            "llm": llm_response,
            "conf": confidence_score,
            "reason": failure_reason,
            "name": suggested_item_name,
            "qty": suggested_quantity,
            "now": _now_iso(),
        },
    )
    return review_id


async def get_pending_reviews(include_reviewed: bool = False) -> list[dict]:
    if include_reviewed:
        return await _execute("SELECT * FROM pending_human_review ORDER BY created_at DESC")
    return await _execute(
        "SELECT * FROM pending_human_review WHERE reviewed = 0 ORDER BY created_at DESC"
    )


async def approve_review(review_id: str) -> Optional[str]:
    """Approve a pending review and add it to active inventory. Returns item_id."""
    rows = await _execute(
        "SELECT * FROM pending_human_review WHERE id = :id", {"id": review_id}
    )
    if not rows:
        return None
    review = rows[0]
    await _execute_write(
        "UPDATE pending_human_review SET reviewed = 1 WHERE id = :id",
        {"id": review_id},
    )
    if review.get("suggested_item_name"):
        item_id = await insert_inventory_item(
            item_name=review["suggested_item_name"],
            category="Other",
            quantity=review.get("suggested_quantity") or 1.0,
            unit="units",
            expiry_date=None,
            co2_per_unit_kg=0.0,
            confidence_score=review.get("confidence_score") or 0.0,
            input_method="MANUAL",
        )
        return item_id
    return None


async def reject_review(review_id: str) -> None:
    await _execute_write(
        "UPDATE pending_human_review SET reviewed = 2 WHERE id = :id",
        {"id": review_id},
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Inventory Events (time-series)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def insert_event(
    *,
    item_id: str,
    timestamp: str,
    action_type: str,
    qty_change: float,
    day_of_week: Optional[int] = None,
    is_weekend: Optional[int] = None,
    notes: Optional[str] = None,
) -> None:
    await _execute_write(
        """INSERT INTO inventory_events
           (item_id, timestamp, action_type, qty_change, day_of_week, is_weekend, notes)
           VALUES (:item_id, :ts, :action, :qty, :dow, :weekend, :notes)""",
        {
            "item_id": item_id,
            "ts": timestamp,
            "action": action_type,
            "qty": qty_change,
            "dow": day_of_week,
            "weekend": is_weekend,
            "notes": notes,
        },
    )


async def get_usage_events(item_id: str, days: int = 30) -> list[dict]:
    sim_date = await get_config("simulated_date")
    if sim_date:
        return await _execute(
            """SELECT * FROM inventory_events
               WHERE item_id = :item_id
                 AND action_type = 'USE'
                 AND date(timestamp) >= date(:ref, :offset)
               ORDER BY timestamp ASC""",
            {"item_id": item_id, "ref": sim_date, "offset": f"-{days} days"},
        )
    return await _execute(
        """SELECT * FROM inventory_events
           WHERE item_id = :item_id
             AND action_type = 'USE'
             AND date(timestamp) >= date('now', :offset)
           ORDER BY timestamp ASC""",
        {"item_id": item_id, "offset": f"-{days} days"},
    )


async def get_all_events(item_id: Optional[str] = None) -> list[dict]:
    if item_id:
        return await _execute(
            "SELECT * FROM inventory_events WHERE item_id = :id ORDER BY timestamp DESC",
            {"id": item_id},
        )
    return await _execute("SELECT * FROM inventory_events ORDER BY timestamp DESC LIMIT 100")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Carbon Impact DB (Green DB)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def fuzzy_match_carbon_db(item_name: str) -> Optional[dict]:
    """Find a carbon impact entry by exact or fuzzy match."""
    # Exact match first
    rows = await _execute(
        "SELECT * FROM carbon_impact_db WHERE LOWER(item_name) = :name",
        {"name": item_name.lower()},
    )
    if rows:
        return rows[0]

    # Fuzzy match
    all_entries = await _execute("SELECT * FROM carbon_impact_db")
    for entry in all_entries:
        similarity = SequenceMatcher(
            None, item_name.lower(), entry["item_name"].lower()
        ).ratio()
        if similarity >= 0.85:
            return entry
    return None


async def insert_carbon_item(
    *,
    item_name: str,
    category: str,
    co2_per_unit_kg: float,
    avg_shelf_life_days: Optional[int] = None,
    preferred_partner: str = "N/A",
) -> None:
    item_id = str(uuid.uuid4())
    await _execute_write(
        """INSERT OR IGNORE INTO carbon_impact_db
           (item_id, item_name, category, co2_per_unit_kg, avg_shelf_life_days, preferred_partner)
           VALUES (:id, :name, :cat, :co2, :shelf, :partner)""",
        {
            "id": item_id,
            "name": item_name.lower(),
            "cat": category,
            "co2": co2_per_unit_kg,
            "shelf": avg_shelf_life_days,
            "partner": preferred_partner,
        },
    )


async def get_partner_for_item(item_name: str) -> list[dict]:
    """Look up partner organisations for an item (for community mesh)."""
    rows = await _execute(
        """SELECT preferred_partner as name, 'partner@example.org' as email
           FROM carbon_impact_db
           WHERE LOWER(item_name) = :name AND preferred_partner != 'N/A'""",
        {"name": item_name.lower()},
    )
    return rows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Triage Actions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def insert_triage_action(
    *,
    item_id: str,
    action_type: str,
    ai_generated: bool,
    ai_bypassed: bool,
    content: Optional[str] = None,
) -> str:
    action_id = str(uuid.uuid4())
    await _execute_write(
        """INSERT INTO triage_actions
           (id, item_id, action_type, ai_generated, ai_bypassed, content, created_at)
           VALUES (:id, :item_id, :action, :ai, :bypass, :content, :now)""",
        {
            "id": action_id,
            "item_id": item_id,
            "action": action_type,
            "ai": 1 if ai_generated else 0,
            "bypass": 1 if ai_bypassed else 0,
            "content": content,
            "now": _now_iso(),
        },
    )
    return action_id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Audit Log
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def log_audit(
    event_type: str,
    *,
    severity: str = "INFO",
    details: Optional[dict] = None,
    input_method: Optional[str] = None,
    model_used: Optional[str] = None,
    latency_ms: Optional[int] = None,
    confidence: Optional[float] = None,
) -> None:
    """Write an entry to the audit log."""
    await _execute_write(
        """INSERT INTO audit_log
           (timestamp, event_type, severity, details, input_method,
            model_used, latency_ms, confidence)
           VALUES (:ts, :evt, :sev, :det, :inp, :model, :lat, :conf)""",
        {
            "ts": _now_iso(),
            "evt": event_type,
            "sev": severity,
            "det": json.dumps(details) if details else None,
            "inp": input_method,
            "model": model_used,
            "lat": latency_ms,
            "conf": confidence,
        },
    )


async def get_audit_logs(
    event_type: Optional[str] = None, limit: int = 50
) -> list[dict]:
    if event_type:
        return await _execute(
            "SELECT * FROM audit_log WHERE event_type = :evt ORDER BY timestamp DESC LIMIT :lim",
            {"evt": event_type, "lim": limit},
        )
    return await _execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT :lim",
        {"lim": limit},
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Forecasts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def upsert_forecast(item_id: str, forecast_data: dict) -> None:
    """Insert or update a forecast for a specific item."""
    # Delete old forecast for this item first
    await _execute_write(
        "DELETE FROM forecasts WHERE item_id = :id", {"id": item_id}
    )
    await _execute_write(
        """INSERT INTO forecasts
           (item_id, predicted_runout_date, days_of_supply, daily_burn_rate,
            weekend_multiplier, r_squared, data_points_used, computed_at)
           VALUES (:id, :runout, :supply, :burn, :wkend, :r2, :pts, :now)""",
        {
            "id": item_id,
            "runout": forecast_data.get("predicted_runout_date"),
            "supply": forecast_data.get("days_of_supply"),
            "burn": forecast_data.get("daily_burn_rate"),
            "wkend": forecast_data.get("weekend_multiplier", 1.0),
            "r2": forecast_data.get("r_squared"),
            "pts": forecast_data.get("data_points_used"),
            "now": _now_iso(),
        },
    )


async def get_forecast(item_id: str) -> Optional[dict]:
    rows = await _execute(
        "SELECT * FROM forecasts WHERE item_id = :id ORDER BY computed_at DESC LIMIT 1",
        {"id": item_id},
    )
    return rows[0] if rows else None


async def get_all_forecasts() -> list[dict]:
    sim_date = await get_config("simulated_date")
    today_expr = f"'{sim_date}'" if sim_date else "date('now')"
    return await _execute(
        f"""SELECT f.*, i.item_name, i.quantity, i.unit, i.category,
               i.expiry_date,
               CASE WHEN i.expiry_date IS NOT NULL
                    THEN CAST(julianday(i.expiry_date) - julianday({today_expr}) AS INTEGER)
                    ELSE NULL END as days_till_expiry,
               CASE
                 WHEN i.expiry_date IS NULL THEN
                   CASE WHEN f.days_of_supply <= 7 THEN 'Understocked'
                        ELSE 'Well Stocked' END
                 WHEN julianday(i.expiry_date) < julianday(f.predicted_runout_date)
                   THEN 'Overstocked'
                 WHEN CAST(julianday(i.expiry_date) - julianday({today_expr}) AS INTEGER)
                      = CAST(julianday(f.predicted_runout_date) - julianday({today_expr}) AS INTEGER)
                   THEN 'Well Stocked'
                 ELSE 'Understocked'
               END as stock_status
           FROM forecasts f
           JOIN inventory_items i ON f.item_id = i.id
           ORDER BY f.days_of_supply ASC"""
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Recipes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def insert_recipe(
    *,
    title: str,
    ingredients_used: list[str],
    instructions: str,
    estimated_servings: int,
    co2_saved_kg: float,
    original_price: float = 0.0,
    suggested_price: float = 0.0,
    discount_percent: int = 0,
    ai_generated: bool = True,
) -> str:
    recipe_id = str(uuid.uuid4())
    await _execute_write(
        """INSERT INTO recipes
           (id, title, ingredients_used, ingredient_names, instructions,
            estimated_servings, co2_saved_kg, original_price, suggested_price,
            discount_percent, ai_generated, created_at)
           VALUES (:id, :title, :ingredients_json, :ingredient_names, :instructions,
                   :servings, :co2, :orig_price, :sugg_price, :disc_pct, :ai, :now)""",
        {
            "id": recipe_id,
            "title": title,
            "ingredients_json": json.dumps(ingredients_used),
            "ingredient_names": ", ".join(ingredients_used),
            "instructions": instructions,
            "servings": estimated_servings,
            "co2": co2_saved_kg,
            "orig_price": original_price,
            "sugg_price": suggested_price,
            "disc_pct": discount_percent,
            "ai": 1 if ai_generated else 0,
            "now": _now_iso(),
        },
    )
    return recipe_id


async def get_recent_recipes(limit: int = 10) -> list[dict]:
    return await _execute(
        "SELECT * FROM recipes ORDER BY created_at DESC LIMIT :lim",
        {"lim": limit},
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  System Config (for Dev Mode)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_config(key: str) -> Optional[str]:
    rows = await _execute(
        "SELECT value FROM system_config WHERE key = :key", {"key": key}
    )
    return rows[0]["value"] if rows else None


async def set_config(key: str, value: str) -> None:
    await _execute_write(
        """INSERT INTO system_config (key, value, updated_at)
           VALUES (:key, :val, :now)
           ON CONFLICT(key) DO UPDATE SET value = :val, updated_at = :now""",
        {"key": key, "val": value, "now": _now_iso()},
    )


async def reset_database() -> None:
    """Drop and recreate all tables. Used for dev mode reset."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database reset complete")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Metrics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_carbon_metrics() -> dict:
    """Calculate carbon impact summary metrics."""
    total_saved = await _execute(
        "SELECT COALESCE(SUM(co2_saved_kg), 0) as total FROM recipes WHERE co2_saved_kg > 0"
    )
    total_footprint = await _execute(
        """SELECT COALESCE(SUM(quantity * co2_per_unit_kg), 0) as total
           FROM inventory_items WHERE co2_per_unit_kg > 0"""
    )
    waste_score = await _execute(
        """SELECT
               COUNT(CASE WHEN status IN ('CONSUMED', 'DONATED') THEN 1 END) as saved,
               COUNT(*) as total
           FROM inventory_items WHERE expiry_date IS NOT NULL"""
    )

    saved = waste_score[0]["saved"] if waste_score else 0
    total = waste_score[0]["total"] if waste_score else 0
    prevention_rate = round((saved / total) * 100, 1) if total > 0 else 0.0

    return {
        "total_co2_saved_kg": round(total_saved[0]["total"], 2) if total_saved else 0.0,
        "total_co2_footprint_kg": round(total_footprint[0]["total"], 2) if total_footprint else 0.0,
        "waste_prevention_rate_pct": prevention_rate,
        "items_saved": saved,
        "items_tracked": total,
    }
