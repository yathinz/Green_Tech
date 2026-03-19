"""
Eco-Pulse V3.0 — Database Seeder
Loads CSV datasets into the SQLite database.
"""

from __future__ import annotations

import csv
import os
import sys
import uuid
from datetime import datetime, timedelta

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
# In Docker, data may be at /app/data
if not os.path.exists(DATA_DIR):
    DATA_DIR = "/app/data"


async def seed_carbon_db() -> int:
    """Load carbon_impact_db.csv into the database."""
    import database as db

    csv_path = os.path.join(DATA_DIR, "carbon_impact_db.csv")
    if not os.path.exists(csv_path):
        print(f"⚠️  {csv_path} not found — skipping carbon DB seed")
        return 0

    count = 0
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            await db.insert_carbon_item(
                item_name=row["item_name"],
                category=row["category"],
                co2_per_unit_kg=float(row["co2_per_unit_kg"]),
                avg_shelf_life_days=int(row["avg_shelf_life_days"]) if row.get("avg_shelf_life_days") else None,
                preferred_partner=row.get("preferred_partner", "N/A"),
            )
            count += 1

    return count


async def seed_inventory_and_events() -> dict:
    """Load mock_inventory_events.csv and create inventory items + events."""
    import database as db

    csv_path = os.path.join(DATA_DIR, "mock_inventory_events.csv")
    if not os.path.exists(csv_path):
        print(f"⚠️  {csv_path} not found — skipping events seed")
        return {"items": 0, "events": 0}

    # Track items we've created
    item_ids: dict[str, str] = {}
    item_quantities: dict[str, float] = {}
    event_count = 0

    # First pass: collect unique items and calculate net quantities
    events = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append(row)
            item_key = row["item_id"]
            if item_key not in item_quantities:
                item_quantities[item_key] = 0.0
            item_quantities[item_key] += float(row["qty_change"])

    # Carbon lookup for items
    carbon_lookup: dict[str, dict] = {}
    carbon_path = os.path.join(DATA_DIR, "carbon_impact_db.csv")
    if os.path.exists(carbon_path):
        with open(carbon_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                carbon_lookup[row["item_name"]] = row

    # ── Realistic seed overrides ────────────────────────────────
    # Hand-tuned quantities & expiry dates to produce a well-spread
    # mix of stock statuses (Understocked / Well Stocked / Overstocked).
    #
    # Status logic: compare predicted runout (today + qty/burn_rate)
    # against expiry_date:
    #   Overstocked  — expiry BEFORE runout  (too much stock, will expire)
    #   Well Stocked — days until runout == days till expiry (exact match)
    #   Understocked — expiry AFTER runout  (will run out before it expires)
    #
    # Base date: March 19, 2026
    SEED_OVERRIDES = {
        # ── OVERSTOCKED (3): huge stock, near expiry ──
        "chicken breast":  {"qty": 8.0,    "unit": "kg",    "expiry": "2026-03-22"},  # ~7d supply, 3d to expiry
        "whole milk":      {"qty": 16.0,   "unit": "L",     "expiry": "2026-03-22"},  # ~7d supply, 3d to expiry
        "sourdough bread": {"qty": 18.0,   "unit": "units", "expiry": "2026-03-22"},  # ~7d supply, 3d to expiry
        # ── WELL STOCKED (4): supply ≈ expiry (gap ≤ 7d) ──
        "greek yogurt":    {"qty": 55.0,   "unit": "units", "expiry": "2026-04-03"},  # ~12d supply, 15d to expiry
        "orange juice":    {"qty": 14.0,   "unit": "L",     "expiry": "2026-04-06"},  # ~16d supply, 18d to expiry
        "cheddar cheese":  {"qty": 5.0,    "unit": "kg",    "expiry": "2026-04-17"},  # ~25d supply, 29d to expiry
        "organic apple":   {"qty": 80.0,   "unit": "units", "expiry": "2026-04-03"},  # ~13d supply, 15d to expiry
        # ── UNDERSTOCKED (3): low stock, long shelf life ──
        "coffee bean":     {"qty": 2500.0, "unit": "g",     "expiry": "2026-06-17"},  # ~15d supply, 90d to expiry
        "tomato":          {"qty": 15.0,   "unit": "units", "expiry": "2026-04-30"},  # ~5d supply, 42d to expiry
        "egg":             {"qty": 36.0,   "unit": "units", "expiry": "2026-04-16"},  # ~4d supply, 28d to expiry
    }

    # Create inventory items from the unique items in events
    for event in events:
        item_key = event["item_id"]
        if item_key not in item_ids:
            item_name = event["item_name"]
            carbon = carbon_lookup.get(item_name, {})

            # Use hand-tuned override if available, otherwise fall back
            override = SEED_OVERRIDES.get(item_name)
            if override:
                net_qty = override["qty"]
                unit = override["unit"]
                expiry = override["expiry"]
                shelf_life = 1  # always has expiry
            else:
                # Fallback: calculate from CSV events
                net_qty = max(abs(item_quantities.get(item_key, 10)), 1.0)

                unit = "units"
                if item_name in ("whole milk", "orange juice"):
                    unit = "L"
                elif item_name in ("coffee bean", "cheddar cheese", "chicken breast"):
                    unit = "kg" if item_name in ("cheddar cheese", "chicken breast") else "g"

                shelf_life = int(carbon.get("avg_shelf_life_days", 14) or 14)
                expiry = (datetime(2026, 3, 19) + timedelta(days=shelf_life // 2)).strftime("%Y-%m-%d")

            item_id = await db.insert_inventory_item(
                item_name=item_name,
                category=carbon.get("category", "Other"),
                quantity=round(net_qty, 1),
                unit=unit,
                expiry_date=expiry if shelf_life > 0 else None,
                co2_per_unit_kg=float(carbon.get("co2_per_unit_kg", 0)),
                confidence_score=0.95,
                input_method="CSV_IMPORT",
            )
            item_ids[item_key] = item_id

    # Insert all events
    for event in events:
        item_key = event["item_id"]
        real_item_id = item_ids.get(item_key, item_key)

        await db.insert_event(
            item_id=real_item_id,
            timestamp=event["timestamp"],
            action_type=event["action_type"],
            qty_change=float(event["qty_change"]),
            day_of_week=int(event.get("day_of_week", 0)),
            is_weekend=int(event.get("is_weekend", 0)),
            notes=event.get("notes", ""),
        )
        event_count += 1

    return {"items": len(item_ids), "events": event_count}


async def seed_all(database_path: str = "/data/ecopulse.db") -> dict:
    """Seed all data into the database."""
    import database as db

    # Ensure DB is initialised
    if db._engine is None:
        await db.init_db(database_path)

    carbon_count = await seed_carbon_db()
    inventory_result = await seed_inventory_and_events()

    # Log the seeding
    await db.log_audit(
        "INGESTION",
        severity="INFO",
        details={
            "action": "SEED_DATA",
            "carbon_items": carbon_count,
            "inventory_items": inventory_result["items"],
            "events": inventory_result["events"],
        },
    )

    return {
        "carbon_items": carbon_count,
        "inventory_items": inventory_result["items"],
        "events": inventory_result["events"],
    }


if __name__ == "__main__":
    import asyncio

    print("🌱 Eco-Pulse V3.0 — Database Seeder\n")
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/data/ecopulse.db"
    result = asyncio.run(seed_all(db_path))
    print(f"\n✅ Seeding complete: {result}")
