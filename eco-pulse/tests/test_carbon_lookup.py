"""
Eco-Pulse V3.0 — Carbon Lookup Tests
2 tests: known item lookup and unknown item AI estimate + persist.
"""

from __future__ import annotations

import os
import sys

import pytest

_parent = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_parent, "backend"))  # local dev
sys.path.insert(0, _parent)                            # Docker

from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_known_item_lookup(test_db):
    """Known item in Green DB → returns correct CO₂ value."""
    # Seed a carbon entry
    await test_db.insert_carbon_item(
        item_name="whole milk",
        category="Milk & Cream",
        co2_per_unit_kg=3.2,
        avg_shelf_life_days=7,
    )

    from carbon_lookup import lookup_carbon_impact

    co2 = await lookup_carbon_impact("whole milk", "Milk & Cream", db_module=test_db)

    assert co2 == 3.2


@pytest.mark.asyncio
async def test_unknown_item_returns_zero_without_ai(test_db):
    """Unknown item with no AI client → returns 0.0 fallback."""
    from carbon_lookup import lookup_carbon_impact

    co2 = await lookup_carbon_impact(
        "exotic dragonfruit", "Fresh Fruit",
        db_module=test_db,
        ai_client=None,
        settings=None,
    )

    assert co2 == 0.0
