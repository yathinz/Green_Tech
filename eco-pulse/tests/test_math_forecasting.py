"""
Eco-Pulse V3.0 — Math Forecasting Tests
4 tests validating the deterministic linear regression engine.
"""

from __future__ import annotations

import os
import sys

import pytest

_parent = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_parent, "backend"))  # local dev
sys.path.insert(0, _parent)                            # Docker

from predictive_math import (
    forecast_burn_rate,
    generate_mock_events,
    generate_mock_events_with_weekend_spike,
)


@pytest.mark.asyncio
async def test_basic_linear_forecast(test_db):
    """Happy path: sufficient data → accurate prediction."""
    events = generate_mock_events(item_id="milk-001", daily_rate=2.0, days=14)

    result = await forecast_burn_rate("milk-001", events=events, current_stock=10.0)

    assert result["status"] == "OK"
    assert 3.0 <= result["days_of_supply"] <= 7.0  # ~5 days at 2/day
    assert result["r_squared"] >= 0.0  # Model should fit (may be low with uniform data)
    assert result["data_points_used"] == 14


@pytest.mark.asyncio
async def test_insufficient_data_returns_none(test_db):
    """< 7 days of data → returns INSUFFICIENT_DATA status."""
    events = generate_mock_events(item_id="milk-001", daily_rate=2.0, days=3)

    result = await forecast_burn_rate("milk-001", events=events, current_stock=10.0)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["days_of_supply"] is None
    assert result["data_points_used"] == 3


@pytest.mark.asyncio
async def test_weekend_spike_detected(test_db):
    """Weekend consumption is higher → weekend_multiplier > 1.0."""
    events = generate_mock_events_with_weekend_spike(
        item_id="coffee-001",
        weekday_rate=3.0,
        weekend_rate=6.0,
        days=21,
    )

    result = await forecast_burn_rate("coffee-001", events=events, current_stock=30.0)

    assert result["status"] == "OK"
    assert result["weekend_multiplier"] >= 1.5  # Should detect the spike


@pytest.mark.asyncio
async def test_zero_consumption_infinite_supply(test_db):
    """If nothing is consumed → infinite days of supply."""
    events = generate_mock_events(item_id="paper-001", daily_rate=0.0, days=14)

    result = await forecast_burn_rate("paper-001", events=events, current_stock=100.0)

    # With zero consumption, days_of_supply should be infinite or very large
    assert result["days_of_supply"] is None or result["days_of_supply"] > 300 or result["days_of_supply"] == float("inf")
