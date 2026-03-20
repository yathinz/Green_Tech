"""
Eco-Pulse V3.0 — Database Seeder
Loads CSV datasets into the SQLite database.
"""

from __future__ import annotations

import csv
import os
import sys
import uuid
from datetime import date, datetime, timedelta

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

    # ── Relative date helpers ───────────────────────────────────
    # All dates are computed relative to today so seeded data stays
    # fresh regardless of when the judge runs the demo.
    today = date.today()
    def d(offset: int) -> str:
        """Return an ISO date string offset days from today."""
        return (today + timedelta(days=offset)).strftime("%Y-%m-%d")

    # Shift CSV event timestamps so the 30-day window ends yesterday
    ORIGINAL_BASE_DATE = date(2026, 3, 19)  # date data was originally authored
    date_offset = timedelta(days=(today - ORIGINAL_BASE_DATE).days)

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

    # Shift all CSV timestamps so the event window is relative to today
    for ev in events:
        original_ts = datetime.strptime(ev["timestamp"], "%Y-%m-%d %H:%M:%S")
        shifted_ts = original_ts + date_offset
        ev["timestamp"] = shifted_ts.strftime("%Y-%m-%d %H:%M:%S")
        ev["day_of_week"] = str(shifted_ts.weekday())
        ev["is_weekend"] = "1" if shifted_ts.weekday() >= 5 else "0"

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
    SEED_OVERRIDES = {
        # ── OVERSTOCKED (3): huge stock, near expiry ──
        "chicken breast":  {"qty": 8.0,    "unit": "kg",    "expiry": d(3)},   # ~7d supply, 3d to expiry
        "whole milk":      {"qty": 16.0,   "unit": "L",     "expiry": d(3)},   # ~7d supply, 3d to expiry
        "sourdough bread": {"qty": 18.0,   "unit": "units", "expiry": d(3)},   # ~7d supply, 3d to expiry
        # ── WELL STOCKED (4): supply ≈ expiry (gap ≤ 7d) ──
        "greek yogurt":    {"qty": 55.0,   "unit": "units", "expiry": d(15)},  # ~12d supply, 15d to expiry
        "orange juice":    {"qty": 14.0,   "unit": "L",     "expiry": d(18)},  # ~16d supply, 18d to expiry
        "cheddar cheese":  {"qty": 5.0,    "unit": "kg",    "expiry": d(29)},  # ~25d supply, 29d to expiry
        "organic apple":   {"qty": 80.0,   "unit": "units", "expiry": d(15)},  # ~13d supply, 15d to expiry
        # ── UNDERSTOCKED (3): low stock, long shelf life ──
        "coffee bean":     {"qty": 2500.0, "unit": "g",     "expiry": d(90)},  # ~15d supply, 90d to expiry
        "tomato":          {"qty": 15.0,   "unit": "units", "expiry": d(42)},  # ~5d supply, 42d to expiry
        "egg":             {"qty": 36.0,   "unit": "units", "expiry": d(28)},  # ~4d supply, 28d to expiry
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
                expiry = (today + timedelta(days=shelf_life // 2)).strftime("%Y-%m-%d")

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

    # ── Historical completed items ──────────────────────────────
    # Portions consumed / donated FROM the current active stock.
    # Each row keeps its quantity as a source of truth, and that
    # same amount is deducted from the active item.
    #
    # Format: (item_name, qty, unit, expiry, status, finished_date, note)
    HISTORICAL_ITEMS = [
        # ── CONSUMED (used up from current batch) ──────────────
        ("whole milk",       3.0,  "L",     d(3),  "CONSUMED", d(-4), "Used for morning prep"),
        ("whole milk",       2.0,  "L",     d(3),  "CONSUMED", d(-1), "Used for recipes"),
        ("chicken breast",   1.5,  "kg",    d(3),  "CONSUMED", d(-3), "Lunch service"),
        ("chicken breast",   1.0,  "kg",    d(3),  "CONSUMED", d(0),  "Dinner service"),
        ("egg",             12.0,  "units", d(28), "CONSUMED", d(-2), "Baking batch"),
        ("greek yogurt",    10.0,  "units", d(15), "CONSUMED", d(-5), "Smoothie station"),
        ("greek yogurt",     8.0,  "units", d(15), "CONSUMED", d(-1), "Staff breakfast"),
        ("organic apple",   15.0,  "units", d(15), "CONSUMED", d(-3), "Juice bar"),
        ("organic apple",   10.0,  "units", d(15), "CONSUMED", d(0),  "Snack station"),
        ("sourdough bread",  4.0,  "units", d(3),  "CONSUMED", d(-2), "Sandwich prep"),
        ("sourdough bread",  3.0,  "units", d(3),  "CONSUMED", d(0),  "Toast service"),
        ("coffee bean",    400.0,  "g",     d(90), "CONSUMED", d(-4), "Daily brewing"),
        ("coffee bean",    350.0,  "g",     d(90), "CONSUMED", d(-1), "Catering order"),
        ("tomato",           3.0,  "units", d(42), "CONSUMED", d(-1), "Salad prep"),
        ("orange juice",     2.0,  "L",     d(18), "CONSUMED", d(-2), "Breakfast bar"),
        ("cheddar cheese",   1.0,  "kg",    d(29), "CONSUMED", d(-3), "Sandwich station"),
        # ── DONATED (given away before expiry) ─────────────────
        ("whole milk",       2.0,  "L",     d(3),  "DONATED",  d(0),  "Donated to FoodRescue Local"),
        ("chicken breast",   1.5,  "kg",    d(3),  "DONATED",  d(0),  "Donated to Food Bank Central"),
        ("sourdough bread",  4.0,  "units", d(3),  "DONATED",  d(0),  "Donated to Shelter Network"),
        ("organic apple",   10.0,  "units", d(15), "DONATED",  d(-1), "Donated to Community Garden"),
        ("greek yogurt",     8.0,  "units", d(15), "DONATED",  d(0),  "Donated to FoodRescue Local"),
        # ── EXPIRED (not rescued in time) ──────────────────────
        ("tomato",           2.0,  "units", d(-4), "EXPIRED",  d(-4), "Expired — composted"),
        ("whole milk",       1.0,  "L",     d(-9), "EXPIRED",  d(-9), "Expired — composted"),
    ]

    # Sum up how much to deduct from each active item
    deductions: dict[str, float] = {}
    for (name, qty, *_rest) in HISTORICAL_ITEMS:
        deductions[name] = deductions.get(name, 0.0) + qty

    # Deduct historical consumed/donated/expired amounts from active rows
    for item_key, active_id in item_ids.items():
        # Find item name from events
        active_name = next(
            (e["item_name"] for e in events if e["item_id"] == item_key), None
        )
        if active_name and active_name in deductions:
            deduct = deductions[active_name]
            # Read current qty from the SEED_OVERRIDE (what we just inserted)
            override = SEED_OVERRIDES.get(active_name)
            if override:
                new_qty = max(override["qty"] - deduct, 0.0)
                await db.update_inventory_item(active_id, quantity=round(new_qty, 1))

    # Insert historical items with their original quantities (source of truth)
    historical_count = 0
    for (name, orig_qty, unit, expiry, status, finished, note) in HISTORICAL_ITEMS:
        carbon = carbon_lookup.get(name, {})
        hist_id = await db.insert_inventory_item(
            item_name=name,
            category=carbon.get("category", "Other"),
            quantity=orig_qty,     # actual qty consumed / donated / expired
            unit=unit,
            expiry_date=expiry,
            co2_per_unit_kg=float(carbon.get("co2_per_unit_kg", 0)),
            confidence_score=0.95,
            input_method="CSV_IMPORT",
            status=status,
        )
        # Matching event so the ledger is complete
        action = "DONATE" if status == "DONATED" else ("WASTE" if status == "EXPIRED" else "USE")
        await db.insert_event(
            item_id=hist_id,
            timestamp=f"{finished} 18:00:00",
            action_type=action,
            qty_change=-orig_qty,
            day_of_week=0,
            is_weekend=0,
            notes=note,
        )
        historical_count += 1
        event_count += 1

    return {
        "items": len(item_ids) + historical_count,
        "events": event_count,
    }


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
