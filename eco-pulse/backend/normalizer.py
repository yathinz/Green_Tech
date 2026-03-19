"""
Eco-Pulse V3.0 — Input Standardisation & Deduplication Pipeline
3-layer normalisation: AI prompt guidance → deterministic Python → DB dedup.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Layer 2a: Name Normalisation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# British → US English spelling variants
SPELLING_MAP: dict[str, str] = {
    "aluminium": "aluminum",
    "colour": "color",
    "flavour": "flavor",
    "yoghurt": "yogurt",
    "grey": "gray",
    "litre": "liter",
    "metre": "meter",
    "catalogue": "catalog",
    "cheque": "check",
    "tonne": "metric ton",
    "centre": "center",
    "fibre": "fiber",
    "organise": "organize",
    "realise": "realize",
    "analyse": "analyze",
}

# Irregular plural → singular
_IRREGULAR_PLURALS: dict[str, str] = {
    "tomatoes": "tomato",
    "potatoes": "potato",
    "mangoes": "mango",
    "loaves": "loaf",
    "knives": "knife",
    "shelves": "shelf",
    "mice": "mouse",
    "geese": "goose",
    "teeth": "tooth",
    "oxen": "ox",
    "children": "child",
    "fish": "fish",
    "sheep": "sheep",
    "dice": "die",
    "halves": "half",
    "leaves": "leaf",
    "lives": "life",
    "wolves": "wolf",
    "calves": "calf",
    "selves": "self",
}


def singularize(word: str) -> str:
    """Rule-based singularisation. Handles common English plural patterns."""
    if len(word) <= 2:
        return word

    if word in _IRREGULAR_PLURALS:
        return _IRREGULAR_PLURALS[word]

    # -ies → -y  (berries → berry)  but not if only 4 chars
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    # -ves → -f  (loaves → loaf — caught above, but for others)
    if word.endswith("ves"):
        return word[:-3] + "f"
    # -ses / -xes / -zes → drop -es
    if word.endswith(("ses", "xes", "zes")):
        return word[:-2]
    # -shes / -ches → drop -es
    if word.endswith(("shes", "ches")):
        return word[:-2]
    # generic -s → drop (but not -ss like "glass")
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word


def normalize_item_name(name: str) -> str:
    """
    Deterministic name normalisation:
    1. Lowercase + strip + collapse whitespace
    2. Apply British→US spelling map
    3. Singularise each word
    """
    # Step 1 — lowercase, strip, collapse whitespace
    name = re.sub(r"\s+", " ", name.strip().lower())

    # Step 2 — apply spelling corrections word-by-word
    words = name.split()
    words = [SPELLING_MAP.get(w, w) for w in words]

    # Step 3 — singularise each word
    words = [singularize(w) for w in words]

    return " ".join(words)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Layer 2b: Unit Normalisation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Conversion table → canonical metric units
UNIT_CONVERSIONS: dict[str, dict[str, float]] = {
    # Volume
    "cup": {"mL": 240},
    "cups": {"mL": 240},
    "tbsp": {"mL": 15},
    "tablespoon": {"mL": 15},
    "tablespoons": {"mL": 15},
    "tsp": {"mL": 5},
    "teaspoon": {"mL": 5},
    "teaspoons": {"mL": 5},
    "gallon": {"L": 3.785},
    "gallons": {"L": 3.785},
    "gal": {"L": 3.785},
    "pint": {"mL": 473},
    "pints": {"mL": 473},
    "quart": {"mL": 946},
    "quarts": {"mL": 946},
    "fl oz": {"mL": 29.57},
    "fl_oz": {"mL": 29.57},
    # Weight
    "lb": {"g": 453.6},
    "lbs": {"g": 453.6},
    "pound": {"g": 453.6},
    "pounds": {"g": 453.6},
    "oz": {"g": 28.35},
    "ounce": {"g": 28.35},
    "ounces": {"g": 28.35},
    # Counting
    "dozen": {"units": 12},
    "pair": {"units": 2},
    "pairs": {"units": 2},
    "gross": {"units": 144},
    "ream": {"units": 500},
    "reams": {"units": 500},
}

# Common pack sizes when AI couldn't resolve (fallback estimates)
DEFAULT_PACK_SIZES: dict[str, dict[str, float]] = {
    "rice": {"g": 1000},
    "white rice": {"g": 1000},
    "basmati rice": {"g": 1000},
    "pasta": {"g": 500},
    "butter": {"g": 250},
    "sugar": {"g": 1000},
    "flour": {"g": 1000},
    "coffee bean": {"g": 500},
    "napkin": {"units": 100},
    "paper towel": {"units": 6},
    "salt": {"g": 500},
    "pepper": {"g": 50},
}

# Canonical casing for the 5 allowed units
_CANONICAL_UNIT_MAP: dict[str, str] = {
    "kg": "kg",
    "g": "g",
    "l": "L",
    "ml": "mL",
    "units": "units",
    "unit": "units",
}


def normalize_quantity_and_unit(
    quantity: float, unit: str, item_name: str = ""
) -> tuple[float, str]:
    """
    Normalise quantity + unit to canonical base units.
    Returns (normalised_quantity, canonical_unit).
    """
    unit_lower = unit.strip().lower()

    # Already canonical?
    if unit_lower in _CANONICAL_UNIT_MAP:
        return (quantity, _CANONICAL_UNIT_MAP[unit_lower])

    # Known conversion?
    if unit_lower in UNIT_CONVERSIONS:
        conv = UNIT_CONVERSIONS[unit_lower]
        target_unit = list(conv.keys())[0]
        factor = list(conv.values())[0]
        return (round(quantity * factor, 2), target_unit)

    # "pack" / "packs" / "package" / "bag" → look up default pack sizes
    if unit_lower in ("pack", "packs", "package", "packages", "bag", "bags"):
        normalised = normalize_item_name(item_name)
        if normalised in DEFAULT_PACK_SIZES:
            conv = DEFAULT_PACK_SIZES[normalised]
            target_unit = list(conv.keys())[0]
            factor = list(conv.values())[0]
            return (round(quantity * factor, 2), target_unit)
        # Unknown pack size — keep as units
        return (quantity, "units")

    # Bottle / can / box / carton / jar → units (AI should have resolved volume)
    if unit_lower in (
        "bottle", "bottles", "can", "cans", "box", "boxes",
        "carton", "cartons", "jar", "jars",
    ):
        return (quantity, "units")

    # Unknown — keep as-is
    return (quantity, unit)


def auto_upscale_unit(quantity: float, unit: str) -> tuple[float, str]:
    """
    Upscale small units for readability:
    - 1500 g → 1.5 kg
    - 2000 mL → 2.0 L
    """
    if unit == "g" and quantity >= 1000:
        return (round(quantity / 1000, 3), "kg")
    if unit == "mL" and quantity >= 1000:
        return (round(quantity / 1000, 3), "L")
    return (quantity, unit)


def convert_to_target_unit(
    quantity: float, from_unit: str, to_unit: str
) -> tuple[float, str]:
    """
    Convert between compatible unit families for merging during dedup.
    Supports: g ↔ kg, mL ↔ L.  Raises ValueError for incompatible families.
    """
    CONVERSIONS: dict[tuple[str, str], float] = {
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000,
        ("mL", "L"): 0.001,
        ("L", "mL"): 1000,
    }
    if from_unit == to_unit:
        return (quantity, to_unit)
    key = (from_unit, to_unit)
    if key not in CONVERSIONS:
        raise ValueError(
            f"Cannot convert {from_unit} to {to_unit}: incompatible unit families"
        )
    return (round(quantity * CONVERSIONS[key], 3), to_unit)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Layer 3: Database-Level Deduplication
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def find_existing_item(
    item_name: str, category: str, expiry_date: Optional[str] = None, db_module=None
) -> Optional[dict]:
    """
    Find an existing active inventory item that matches the incoming item.
    Composite key: item_name + expiry_date.
    - Same item with different expiry dates → separate entries.
    - Same item with same expiry date → merge quantities.
    1. Exact match on normalised name + category + expiry_date
    2. Fuzzy match (≥ 85% similarity) within same category AND same expiry_date
    """
    if db_module is None:
        import database as db_module  # noqa: F811

    normalised = normalize_item_name(item_name)

    # Step 1 — exact match (name + category + expiry_date)
    if expiry_date:
        exact = await db_module._execute(
            "SELECT * FROM inventory_items WHERE "
            "LOWER(item_name) = :name AND category = :cat "
            "AND expiry_date = :exp AND status = 'ACTIVE'",
            {"name": normalised, "cat": category, "exp": expiry_date},
        )
    else:
        exact = await db_module._execute(
            "SELECT * FROM inventory_items WHERE "
            "LOWER(item_name) = :name AND category = :cat "
            "AND expiry_date IS NULL AND status = 'ACTIVE'",
            {"name": normalised, "cat": category},
        )
    if exact:
        return exact[0]

    # Step 2 — fuzzy match within same category AND same expiry_date
    if expiry_date:
        all_items = await db_module._execute(
            "SELECT * FROM inventory_items WHERE category = :cat "
            "AND expiry_date = :exp AND status = 'ACTIVE'",
            {"cat": category, "exp": expiry_date},
        )
    else:
        all_items = await db_module._execute(
            "SELECT * FROM inventory_items WHERE category = :cat "
            "AND expiry_date IS NULL AND status = 'ACTIVE'",
            {"cat": category},
        )
    for existing in all_items:
        similarity = SequenceMatcher(
            None, normalised, existing["item_name"].lower()
        ).ratio()
        if similarity >= 0.85:
            return existing

    return None


async def upsert_inventory_item(
    extracted_item, carbon_score: float, input_method: str, db_module=None
) -> dict:
    """
    Insert or merge an item into inventory.
    - If item exists → ADD to existing quantity (and update expiry if sooner)
    - If new → INSERT new row
    """
    if db_module is None:
        import database as db_module  # noqa: F811

    # Normalise all fields
    normalised_name = normalize_item_name(extracted_item.item_name)
    qty, unit = normalize_quantity_and_unit(
        extracted_item.quantity, extracted_item.unit.value
        if hasattr(extracted_item.unit, "value") else extracted_item.unit,
        extracted_item.item_name,
    )
    qty, unit = auto_upscale_unit(qty, unit)

    category_val = (
        extracted_item.category.value
        if hasattr(extracted_item.category, "value")
        else extracted_item.category
    )

    # Check for existing item (composite key: name + expiry_date)
    existing = await find_existing_item(
        normalised_name, category_val, extracted_item.expiry_date, db_module
    )

    if existing:
        # MERGE — same item AND same expiry → add quantities
        if existing["unit"] == unit:
            new_qty = existing["quantity"] + qty
        else:
            try:
                converted_qty, _ = convert_to_target_unit(qty, unit, existing["unit"])
                new_qty = existing["quantity"] + converted_qty
                unit = existing["unit"]
            except ValueError:
                new_qty = existing["quantity"] + qty

        await db_module.update_inventory_item(
            existing["id"], quantity=new_qty, co2_per_unit_kg=carbon_score
        )
        await db_module.log_audit(
            "ITEM_MERGED",
            details={
                "existing_item": existing["item_name"],
                "incoming_name": extracted_item.item_name,
                "expiry_date": extracted_item.expiry_date,
                "added_qty": qty,
                "new_total": new_qty,
                "unit": unit,
                "co2_per_unit_kg": carbon_score,
            },
        )
        return {"action": "MERGED", "item_id": existing["id"], "new_qty": new_qty}
    else:
        # INSERT
        item_id = await db_module.insert_inventory_item(
            item_name=normalised_name,
            category=category_val,
            quantity=qty,
            unit=unit,
            expiry_date=extracted_item.expiry_date,
            co2_per_unit_kg=carbon_score,
            confidence_score=extracted_item.confidence_score,
            input_method=input_method,
        )
        return {"action": "INSERTED", "item_id": item_id}
