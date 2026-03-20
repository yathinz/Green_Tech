"""
Eco-Pulse V3.0 — Synthetic Data Generator
Generates reproducible CSV datasets for demos and Grafana dashboards.
Uses numpy.random with a fixed seed for reproducibility.
"""

from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta

import numpy as np

# Fixed seed for reproducibility
np.random.seed(42)
random.seed(42)

# ── Output paths ─────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Carbon Impact DB (Green DB)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CARBON_DATA = [
    # item_name, category, co2_per_unit_kg, avg_shelf_life_days, preferred_partner
    ("whole milk", "Milk & Cream", 3.2, 7, "FoodRescue Local"),
    ("cheddar cheese", "Cheese", 13.5, 30, "FoodRescue Local"),
    ("greek yogurt", "Yogurt", 3.5, 14, "FoodRescue Local"),
    ("butter", "Butter & Spreads", 12.1, 60, "N/A"),
    ("egg", "Eggs", 0.35, 28, "FoodRescue Local"),
    ("organic apple", "Fresh Fruit", 0.4, 21, "Community Garden"),
    ("banana", "Fresh Fruit", 0.7, 7, "Community Garden"),
    ("tomato", "Fresh Vegetables", 1.4, 10, "Community Garden"),
    ("lettuce", "Herbs & Leafy Greens", 0.3, 5, "Community Garden"),
    ("carrot", "Root Vegetables", 0.3, 21, "Community Garden"),
    ("chicken breast", "Poultry", 6.9, 3, "Food Bank Central"),
    ("ground beef", "Red Meat", 27.0, 3, "Food Bank Central"),
    ("salmon fillet", "Seafood", 5.1, 2, "Food Bank Central"),
    ("sourdough bread", "Bread & Rolls", 0.9, 5, "Shelter Network"),
    ("croissant", "Pastry & Cakes", 1.3, 3, "Shelter Network"),
    ("bagel", "Bread & Rolls", 0.8, 4, "Shelter Network"),
    ("orange juice", "Juice & Soft Drinks", 0.7, 10, "N/A"),
    ("coffee bean", "Coffee & Tea", 8.0, 180, "N/A"),
    ("oat milk", "Plant-Based Milk", 0.9, 14, "N/A"),
    ("white rice", "Grains & Rice", 2.7, 365, "N/A"),
    ("pasta", "Pasta & Noodles", 0.9, 365, "N/A"),
    ("olive oil", "Cooking Oils & Vinegar", 3.3, 365, "N/A"),
    ("printer paper", "Office - Paper", 1.1, 0, "N/A"),
    ("cleaning spray", "Cleaning Products", 0.5, 365, "N/A"),
    ("hand sanitizer", "Cleaning Products", 0.3, 730, "N/A"),
    ("lab ethanol", "Lab Chemicals", 2.0, 365, "University Recycle"),
    ("petri dish", "Lab Equipment", 0.8, 0, "N/A"),
    ("whiteboard marker", "Office - Supplies", 0.2, 180, "N/A"),
    ("napkin", "Office - Paper", 0.4, 0, "N/A"),
    ("sugar", "Sugar & Sweeteners", 0.8, 730, "N/A"),
]


def generate_carbon_csv():
    """Generate data/carbon_impact_db.csv."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, "carbon_impact_db.csv")

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_name", "category", "co2_per_unit_kg",
            "avg_shelf_life_days", "preferred_partner",
        ])
        for row in CARBON_DATA:
            writer.writerow(row)

    print(f"✅ Generated {filepath} ({len(CARBON_DATA)} items)")
    return filepath


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Mock Inventory Events (time-series)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Items that generate events  (subset of carbon DB with typical usage)
EVENT_ITEMS = [
    {"id": "milk-001",     "name": "whole milk",     "unit": "L",     "base_rate": 3.0},
    {"id": "coffee-001",   "name": "coffee bean",    "unit": "g",     "base_rate": 200},
    {"id": "apple-001",    "name": "organic apple",  "unit": "units", "base_rate": 8.0},
    {"id": "bread-001",    "name": "sourdough bread","unit": "units", "base_rate": 4.0},
    {"id": "egg-001",      "name": "egg",            "unit": "units", "base_rate": 12.0},
    {"id": "cheese-001",   "name": "cheddar cheese", "unit": "kg",    "base_rate": 0.3},
    {"id": "yogurt-001",   "name": "greek yogurt",   "unit": "units", "base_rate": 5.0},
    {"id": "tomato-001",   "name": "tomato",         "unit": "units", "base_rate": 4.0},
    {"id": "chicken-001",  "name": "chicken breast",  "unit": "kg",    "base_rate": 1.5},
    {"id": "oj-001",       "name": "orange juice",   "unit": "L",     "base_rate": 1.0},
]

# Realistic note templates
USE_NOTES = [
    "Morning rush", "Lunch prep", "Afternoon service", "Evening special",
    "Catering order", "Staff meal", "Smoothie bar", "Baking batch",
    "Daily prep", "Customer order", "Recipe testing", "Breakfast service",
]
ADD_NOTES = [
    "Weekly delivery", "Emergency restock", "Supplier drop-off",
    "Farmers market purchase", "Wholesale order",
]
WASTE_NOTES = [
    "Expired — composted", "Quality issue", "Damaged in storage",
    "Past expiry date", "Mould found",
]


def generate_events_csv(days: int = 30) -> str:
    """Generate data/mock_inventory_events.csv with ~500 rows."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, "mock_inventory_events.csv")

    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
    events = []
    event_id = 1

    for d in range(days):
        current_date = base_date + timedelta(days=d)
        dow = current_date.weekday()
        is_weekend = dow >= 5
        weekend_mult = 1.6 if is_weekend else 1.0

        for item in EVENT_ITEMS:
            # Determine how many events for this item today
            n_events = np.random.poisson(lam=2)  # ~2 events per item per day
            if is_weekend:
                n_events = int(n_events * 1.3)

            for _ in range(n_events):
                # 70% USE, 15% ADD, 10% RESTOCK, 5% WASTE
                r = np.random.random()
                if r < 0.70:
                    action = "USE"
                    qty = -round(
                        item["base_rate"] / 3 * weekend_mult * np.random.uniform(0.5, 1.5), 2
                    )
                    notes = random.choice(USE_NOTES)
                elif r < 0.85:
                    action = "ADD"
                    qty = round(item["base_rate"] * np.random.uniform(2, 5), 2)
                    notes = random.choice(ADD_NOTES)
                elif r < 0.95:
                    action = "RESTOCK"
                    qty = round(item["base_rate"] * np.random.uniform(3, 8), 2)
                    notes = random.choice(ADD_NOTES)
                else:
                    action = "WASTE"
                    qty = -round(item["base_rate"] / 5 * np.random.uniform(0.3, 1.0), 2)
                    notes = random.choice(WASTE_NOTES)

                # Random time during business hours (7:00-20:00)
                hour = np.random.randint(7, 20)
                minute = np.random.randint(0, 59)
                ts = current_date.replace(hour=hour, minute=minute)

                events.append({
                    "event_id": event_id,
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "item_id": item["id"],
                    "item_name": item["name"],
                    "action_type": action,
                    "qty_change": qty,
                    "day_of_week": dow,
                    "is_weekend": 1 if is_weekend else 0,
                    "notes": notes,
                })
                event_id += 1

    # Sort by timestamp
    events.sort(key=lambda e: e["timestamp"])

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "event_id", "timestamp", "item_id", "item_name",
            "action_type", "qty_change", "day_of_week", "is_weekend", "notes",
        ])
        writer.writeheader()
        writer.writerows(events)

    print(f"✅ Generated {filepath} ({len(events)} events over {days} days)")
    return filepath


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


if __name__ == "__main__":
    print("🌍 Eco-Pulse V3.0 — Synthetic Data Generator\n")
    generate_carbon_csv()
    generate_events_csv(days=30)
    print("\n✅ All datasets generated!")
