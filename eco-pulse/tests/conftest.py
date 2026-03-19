"""
Eco-Pulse V3.0 — Shared Test Fixtures
Provides in-memory SQLite, mock Gemini client, sample data, and test settings.
"""

from __future__ import annotations

import os
import sys

import pytest
import pytest_asyncio

# Ensure backend is importable — in Docker, backend code is at /app/
_parent = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_parent, "backend"))  # local dev
sys.path.insert(0, _parent)                            # Docker (/app/)

from unittest.mock import AsyncMock, MagicMock, patch

from schemas import (
    ExtractionResult,
    ExtractedItem,
    ItemCategory,
    ItemUnit,
    Recipe,
    RecipeResponse,
)


# ── In-memory database ──────────────────────────────────

@pytest_asyncio.fixture
async def test_db():
    """
    In-memory SQLite database for testing.
    Creates all tables, yields for test, then tears down.
    """
    import database as db

    await db.init_db(":memory:")
    yield db
    # Teardown
    if db._engine:
        async with db._engine.begin() as conn:
            from models import Base
            await conn.run_sync(Base.metadata.drop_all)
        await db._engine.dispose()
        db._engine = None
        db._session_factory = None


# ── Mock Gemini client ───────────────────────────────────

@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client with configurable responses."""
    client = MagicMock()
    client.models.generate_content = MagicMock()
    return client


# ── Sample extraction results ────────────────────────────

@pytest.fixture
def sample_extraction_result():
    """Sample successful extraction result for testing."""
    return ExtractionResult(
        items=[
            ExtractedItem(
                item_name="whole milk",
                quantity=10,
                unit=ItemUnit.LITERS,
                category=ItemCategory.MILK_CREAM,
                confidence_score=0.94,
                expiry_date="2026-03-25",
                raw_input_text="10L whole milk",
            ),
            ExtractedItem(
                item_name="organic apple",
                quantity=50,
                unit=ItemUnit.UNITS,
                category=ItemCategory.FRESH_FRUIT,
                confidence_score=0.91,
                expiry_date="2026-03-28",
                raw_input_text="50 organic apples",
            ),
        ],
        source_description="Test receipt",
    )


@pytest.fixture
def low_confidence_result():
    """Extraction result with low confidence items."""
    return ExtractionResult(
        items=[
            ExtractedItem(
                item_name="mystery item",
                quantity=5,
                unit=ItemUnit.UNITS,
                category=ItemCategory.OTHER,
                confidence_score=0.45,
                expiry_date=None,
                raw_input_text="some blurry text",
            ),
        ],
        source_description="Blurry receipt",
    )


@pytest.fixture
def mixed_confidence_result():
    """Extraction result with mixed confidence items."""
    return ExtractionResult(
        items=[
            ExtractedItem(
                item_name="whole milk",
                quantity=10,
                unit=ItemUnit.LITERS,
                category=ItemCategory.MILK_CREAM,
                confidence_score=0.92,
                expiry_date="2026-03-25",
                raw_input_text="10L whole milk",
            ),
            ExtractedItem(
                item_name="unknown item",
                quantity=5,
                unit=ItemUnit.UNITS,
                category=ItemCategory.OTHER,
                confidence_score=0.45,
                expiry_date=None,
                raw_input_text="??? blurry",
            ),
        ],
        source_description="Partially readable receipt",
    )


@pytest.fixture
def empty_extraction_result():
    """Empty extraction result (F5 trigger)."""
    return ExtractionResult(items=[], source_description="Unreadable input")


@pytest.fixture
def sample_recipe_response():
    """Sample recipe generation response."""
    return RecipeResponse(
        recipes=[
            Recipe(
                title="Creamy Milk Pudding",
                ingredients_used=["whole milk"],
                additional_ingredients=["sugar", "cornstarch"],
                instructions="Heat milk, add sugar and cornstarch, stir until thick. Chill and serve.",
                estimated_servings=6,
                difficulty="Easy",
            ),
        ],
        items_not_used=[],
    )


# ── Test settings ────────────────────────────────────────

@pytest.fixture
def test_settings():
    """Test settings with defaults — uses a fake API key."""
    from config import Settings

    return Settings(
        gemini_api_key="test-key-not-real",
        model_name="gemini-2.5-flash",
        confidence_threshold=0.85,
        llm_timeout_seconds=60,
        database_path=":memory:",
        dev_mode=True,
    )


# ── Seeded database ─────────────────────────────────────

@pytest_asyncio.fixture
async def seeded_db(test_db):
    """
    Database pre-loaded with sample inventory, events, and carbon data.
    """
    # Insert carbon data
    await test_db.insert_carbon_item(
        item_name="whole milk",
        category="Milk & Cream",
        co2_per_unit_kg=3.2,
        avg_shelf_life_days=7,
        preferred_partner="FoodRescue Local",
    )
    await test_db.insert_carbon_item(
        item_name="organic apple",
        category="Fresh Fruit",
        co2_per_unit_kg=0.4,
        avg_shelf_life_days=21,
        preferred_partner="Community Garden",
    )
    await test_db.insert_carbon_item(
        item_name="chicken breast",
        category="Poultry",
        co2_per_unit_kg=6.9,
        avg_shelf_life_days=3,
        preferred_partner="Food Bank Central",
    )

    # Insert inventory items
    milk_id = await test_db.insert_inventory_item(
        item_name="whole milk",
        category="Milk & Cream",
        quantity=10.0,
        unit="L",
        expiry_date="2026-03-22",
        co2_per_unit_kg=3.2,
        confidence_score=0.95,
        input_method="IMAGE",
    )
    apple_id = await test_db.insert_inventory_item(
        item_name="organic apple",
        category="Fresh Fruit",
        quantity=50.0,
        unit="units",
        expiry_date="2026-03-28",
        co2_per_unit_kg=0.4,
        confidence_score=0.91,
        input_method="TEXT",
    )

    # Insert usage events (14 days of data for forecast tests)
    from datetime import datetime, timedelta

    base = datetime(2026, 3, 5)
    for d in range(14):
        dt = base + timedelta(days=d)
        is_weekend = dt.weekday() >= 5
        milk_usage = 3.0 if is_weekend else 2.0
        apple_usage = 8.0 if is_weekend else 5.0

        await test_db.insert_event(
            item_id=milk_id,
            timestamp=dt.strftime("%Y-%m-%d 12:00:00"),
            action_type="USE",
            qty_change=-milk_usage,
            day_of_week=dt.weekday(),
            is_weekend=1 if is_weekend else 0,
            notes="Test event",
        )
        await test_db.insert_event(
            item_id=apple_id,
            timestamp=dt.strftime("%Y-%m-%d 12:00:00"),
            action_type="USE",
            qty_change=-apple_usage,
            day_of_week=dt.weekday(),
            is_weekend=1 if is_weekend else 0,
            notes="Test event",
        )

    yield test_db, {"milk_id": milk_id, "apple_id": apple_id}
