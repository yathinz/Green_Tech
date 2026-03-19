# 📊 Eco-Pulse V3.0 — Synthetic Datasets

## Data Sources & Methodology

All data in this directory is **synthetic** — generated for demonstration and testing purposes.

### `carbon_impact_db.csv` — Green DB Lookup Table

- **30 items** across all categories (dairy, produce, meat, bakery, pantry, beverages, non-food)
- CO₂ values sourced from published lifecycle analysis data:
  - [Our World in Data — Food Choice vs. Eating Local](https://ourworldindata.org/food-choice-vs-eating-local) (CC BY 4.0)
  - DEFRA UK Government Emission Factors (Open Government License)
  - [Open Food Facts](https://world.openfoodfacts.org) (Open Database License)
- Values represent **kg CO₂ per unit** of the item (per L, per kg, per unit, etc.)
- Shelf life estimates are averages for properly stored items

### `mock_inventory_events.csv` — Time-Series Usage Data

- **~500 events** over 30 days (Feb 17 – Mar 18, 2026)
- 10 tracked items with realistic consumption patterns
- **Weekend spikes**: 1.6× more consumption on Saturday/Sunday (simulating café foot traffic)
- **Action type distribution**: USE (70%), ADD (15%), RESTOCK (10%), WASTE (5%)
- Events span 7:00–20:00 business hours with randomised timestamps
- Generated with `numpy.random` using seed 42 for reproducibility

### Generation

```bash
# Regenerate both CSVs:
python scripts/generate_synthetic_data.py
```

## Attribution

| Source | License | Usage |
|--------|---------|-------|
| Our World in Data | CC BY 4.0 | Per-kg CO₂ values for food categories |
| DEFRA | Open Government License | Cross-reference for common items |
| Open Food Facts | Open Database License | Environmental scores reference |
