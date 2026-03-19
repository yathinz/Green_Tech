"""
Tests for the Community Mesh donation partner matching feature.
Verifies partner listing, donation matching, and donation recording.
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_get_all_partners(test_db):
    """Partners registered in carbon DB are listed with their accepted items."""
    db = test_db
    await db.insert_carbon_item(
        item_name="whole milk",
        category="Milk & Cream",
        co2_per_unit_kg=3.2,
        avg_shelf_life_days=7,
        preferred_partner="FoodRescue Local",
    )
    await db.insert_carbon_item(
        item_name="banana",
        category="Fresh Fruit",
        co2_per_unit_kg=0.7,
        avg_shelf_life_days=7,
        preferred_partner="Community Garden",
    )
    await db.insert_carbon_item(
        item_name="olive oil",
        category="Cooking Oils & Vinegar",
        co2_per_unit_kg=3.3,
        avg_shelf_life_days=365,
        preferred_partner="N/A",
    )

    partners = await db.get_all_partners()
    names = [p["name"] for p in partners]
    assert "FoodRescue Local" in names
    assert "Community Garden" in names
    assert "N/A" not in names  # N/A should be excluded


@pytest.mark.asyncio
async def test_find_donation_matches(test_db):
    """Expiring items with a registered partner show up as donation matches."""
    db = test_db
    from datetime import datetime, timedelta

    # Insert carbon entry with a partner
    await db.insert_carbon_item(
        item_name="chicken breast",
        category="Poultry",
        co2_per_unit_kg=6.9,
        avg_shelf_life_days=3,
        preferred_partner="Food Bank Central",
    )

    # Insert an inventory item expiring in 2 days
    today = datetime.now()
    expiry = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    await db.insert_inventory_item(
        item_name="chicken breast",
        category="Poultry",
        quantity=5.0,
        unit="kg",
        expiry_date=expiry,
        co2_per_unit_kg=6.9,
        confidence_score=0.95,
        input_method="TEXT",
    )

    matches = await db.find_donation_matches(days=7)
    assert len(matches) >= 1
    match = matches[0]
    assert match["item_name"] == "chicken breast"
    assert match["partner_name"] == "Food Bank Central"


@pytest.mark.asyncio
async def test_no_match_for_items_without_partner(test_db):
    """Items without a preferred partner (N/A) should not appear in matches."""
    db = test_db
    from datetime import datetime, timedelta

    await db.insert_carbon_item(
        item_name="olive oil",
        category="Cooking Oils & Vinegar",
        co2_per_unit_kg=3.3,
        avg_shelf_life_days=365,
        preferred_partner="N/A",
    )

    expiry = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    await db.insert_inventory_item(
        item_name="olive oil",
        category="Cooking Oils & Vinegar",
        quantity=2.0,
        unit="L",
        expiry_date=expiry,
        co2_per_unit_kg=3.3,
        confidence_score=0.90,
        input_method="TEXT",
    )

    matches = await db.find_donation_matches(days=7)
    partner_items = [m["item_name"] for m in matches]
    assert "olive oil" not in partner_items


@pytest.mark.asyncio
async def test_record_donation(test_db):
    """Recording a donation updates status, logs event, creates triage action, and calculates CO₂."""
    db = test_db
    from datetime import datetime, timedelta

    await db.insert_carbon_item(
        item_name="sourdough bread",
        category="Bread & Rolls",
        co2_per_unit_kg=0.9,
        avg_shelf_life_days=5,
        preferred_partner="Shelter Network",
    )

    expiry = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    item_id = await db.insert_inventory_item(
        item_name="sourdough bread",
        category="Bread & Rolls",
        quantity=10.0,
        unit="units",
        expiry_date=expiry,
        co2_per_unit_kg=0.9,
        confidence_score=0.92,
        input_method="CSV_IMPORT",
    )

    result = await db.record_donation(item_id=item_id, partner_name="Shelter Network")

    assert result["status"] == "DONATED"
    assert result["donated_to"] == "Shelter Network"
    assert result["co2_saved_kg"] == 9.0  # 10 units × 0.9 kg CO₂
    assert "email_payload" in result
    assert "Shelter Network" in result["email_payload"]["body"]

    # Verify item status changed
    item = await db.get_item(item_id)
    assert item["status"] == "DONATED"

    # Verify audit log
    logs = await db.get_audit_logs(event_type="COMMUNITY_MESH")
    assert len(logs) >= 1
    details = json.loads(logs[0]["details"])
    assert details["partner"] == "Shelter Network"
    assert details["co2_saved_kg"] == 9.0


@pytest.mark.asyncio
async def test_record_donation_item_not_found(test_db):
    """Recording a donation for a non-existent item returns an error."""
    db = test_db
    result = await db.record_donation(item_id="nonexistent-id", partner_name="Test")
    assert "error" in result
