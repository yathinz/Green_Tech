"""
Eco-Pulse V3.0 — Normalizer Tests
5 tests covering name normalization, unit conversion, pack sizes, and auto-upscale.
"""

from __future__ import annotations

import os
import sys

_parent = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_parent, "backend"))  # local dev
sys.path.insert(0, _parent)                            # Docker

from normalizer import (
    auto_upscale_unit,
    convert_to_target_unit,
    normalize_item_name,
    normalize_quantity_and_unit,
    singularize,
)
import pytest


def test_name_normalization_plurals_and_casing():
    """Plural forms, mixed case, extra whitespace → canonical singular lowercase."""
    assert normalize_item_name("Apples") == "apple"
    assert normalize_item_name("  ORGANIC  Apples  ") == "organic apple"
    assert normalize_item_name("Tomatoes") == "tomato"
    assert normalize_item_name("Berries") == "berry"
    assert normalize_item_name("Boxes") == "box"


def test_name_normalization_spelling_variants():
    """British → US English spelling normalisation."""
    assert normalize_item_name("aluminium foil") == "aluminum foil"
    assert normalize_item_name("Yoghurt") == "yogurt"
    assert normalize_item_name("natural flavour yoghurt") == "natural flavor yogurt"


def test_unit_conversion_known_units():
    """Common cooking/imperial units → canonical metric units."""
    qty, unit = normalize_quantity_and_unit(1, "cup", "rice")
    assert unit == "mL"
    assert qty == 240

    qty, unit = normalize_quantity_and_unit(2, "lbs", "chicken")
    assert unit == "g"
    assert qty == 907.2

    qty, unit = normalize_quantity_and_unit(1, "gallon", "milk")
    assert unit == "L"
    assert qty == 3.79  # round(3.785, 2)

    qty, unit = normalize_quantity_and_unit(1, "dozen", "egg")
    assert unit == "units"
    assert qty == 12


def test_pack_size_resolution():
    """Ambiguous 'packs' → resolved via DEFAULT_PACK_SIZES table."""
    qty, unit = normalize_quantity_and_unit(2, "packs", "rice")
    assert unit == "g"
    assert qty == 2000  # 2 packs × 1000g

    qty, unit = normalize_quantity_and_unit(1, "pack", "butter")
    assert unit == "g"
    assert qty == 250

    # Unknown pack size → falls back to units
    qty, unit = normalize_quantity_and_unit(3, "packs", "mystery item")
    assert unit == "units"
    assert qty == 3


def test_auto_upscale():
    """Large sub-units get upscaled for readability."""
    qty, unit = auto_upscale_unit(1500, "g")
    assert qty == 1.5
    assert unit == "kg"

    qty, unit = auto_upscale_unit(2000, "mL")
    assert qty == 2.0
    assert unit == "L"

    # Below threshold → no change
    qty, unit = auto_upscale_unit(500, "g")
    assert qty == 500
    assert unit == "g"


def test_convert_to_target_unit():
    """Unit family conversions for merge dedup."""
    qty, unit = convert_to_target_unit(1500, "g", "kg")
    assert unit == "kg"
    assert qty == 1.5

    qty, unit = convert_to_target_unit(2, "kg", "g")
    assert unit == "g"
    assert qty == 2000

    # Incompatible units raise ValueError
    with pytest.raises(ValueError):
        convert_to_target_unit(100, "g", "L")
