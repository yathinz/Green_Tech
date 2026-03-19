"""
Eco-Pulse — Field Population Tests
Verifies CO₂ lookup (token/substring matching), expiry estimation,
and CSV import auto-population of missing fields.
"""

from __future__ import annotations

import os
import sys

import pytest
import pytest_asyncio

_parent = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_parent, "backend"))
sys.path.insert(0, _parent)


# ── Carbon Fuzzy Match: token / substring ────────────────


@pytest.mark.asyncio
async def test_token_match_penne_pasta(test_db):
    """'penne pasta' should match carbon DB entry 'pasta' via token matching."""
    await test_db.insert_carbon_item(
        item_name="pasta",
        category="Pasta & Noodles",
        co2_per_unit_kg=0.9,
        avg_shelf_life_days=365,
    )

    match = await test_db.fuzzy_match_carbon_db("penne pasta")
    assert match is not None
    assert match["co2_per_unit_kg"] == 0.9


@pytest.mark.asyncio
async def test_substring_match_chopped_tomato(test_db):
    """'chopped tomato' should match 'tomato' via substring containment."""
    await test_db.insert_carbon_item(
        item_name="tomato",
        category="Fresh Vegetables",
        co2_per_unit_kg=1.4,
        avg_shelf_life_days=10,
    )

    match = await test_db.fuzzy_match_carbon_db("chopped tomato")
    assert match is not None
    assert match["co2_per_unit_kg"] == 1.4


@pytest.mark.asyncio
async def test_exact_match_still_works(test_db):
    """Exact matches still take priority."""
    await test_db.insert_carbon_item(
        item_name="carrot",
        category="Root Vegetables",
        co2_per_unit_kg=0.3,
        avg_shelf_life_days=21,
    )

    match = await test_db.fuzzy_match_carbon_db("carrot")
    assert match is not None
    assert match["co2_per_unit_kg"] == 0.3


@pytest.mark.asyncio
async def test_no_false_positive(test_db):
    """Completely unrelated item should NOT match."""
    await test_db.insert_carbon_item(
        item_name="pasta",
        category="Pasta & Noodles",
        co2_per_unit_kg=0.9,
        avg_shelf_life_days=365,
    )

    match = await test_db.fuzzy_match_carbon_db("laptop computer")
    assert match is None


# ── Expiry Estimation ────────────────────────────────────


@pytest.mark.asyncio
async def test_expiry_estimated_from_shelf_life(test_db):
    """Items with avg_shelf_life_days get an estimated expiry date."""
    await test_db.insert_carbon_item(
        item_name="carrot",
        category="Root Vegetables",
        co2_per_unit_kg=0.3,
        avg_shelf_life_days=21,
    )

    from carbon_lookup import estimate_expiry_date

    expiry = await estimate_expiry_date(
        "carrot", from_date="2026-03-20", db_module=test_db
    )
    assert expiry == "2026-04-10"  # 2026-03-20 + 21 days


@pytest.mark.asyncio
async def test_no_expiry_for_non_perishable(test_db):
    """Items with shelf_life 0 or None → no expiry estimated."""
    await test_db.insert_carbon_item(
        item_name="printer paper",
        category="Office - Paper",
        co2_per_unit_kg=1.1,
        avg_shelf_life_days=0,
    )

    from carbon_lookup import estimate_expiry_date

    expiry = await estimate_expiry_date(
        "printer paper", from_date="2026-03-20", db_module=test_db
    )
    assert expiry is None


@pytest.mark.asyncio
async def test_expiry_estimation_token_match(test_db):
    """Expiry estimation should work through token-based carbon matching."""
    await test_db.insert_carbon_item(
        item_name="tomato",
        category="Fresh Vegetables",
        co2_per_unit_kg=1.4,
        avg_shelf_life_days=10,
    )

    from carbon_lookup import estimate_expiry_date

    expiry = await estimate_expiry_date(
        "chopped tomato", from_date="2026-03-20", db_module=test_db
    )
    assert expiry == "2026-03-30"  # 2026-03-20 + 10 days


# ── CO₂ lookup via carbon_lookup module ──────────────────


@pytest.mark.asyncio
async def test_carbon_lookup_token_match(test_db):
    """lookup_carbon_impact finds CO₂ via token match."""
    await test_db.insert_carbon_item(
        item_name="pasta",
        category="Pasta & Noodles",
        co2_per_unit_kg=0.9,
        avg_shelf_life_days=365,
    )

    from carbon_lookup import lookup_carbon_impact

    co2 = await lookup_carbon_impact("penne pasta", "Pasta & Noodles", db_module=test_db)
    assert co2 == 0.9
