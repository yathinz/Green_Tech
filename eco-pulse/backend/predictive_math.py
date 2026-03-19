"""
Eco-Pulse V3.0 — Predictive Analytics
Linear Regression with day-of-week seasonality features.
Deterministic math — no AI — for reproducible, fast forecasting.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from sklearn.linear_model import LinearRegression

logger = logging.getLogger("ecopulse.forecast")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Feature Engineering
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def one_hot_day_of_week(dow: int) -> list[int]:
    """One-hot encode day of week (0=Mon … 6=Sun) → 7-element list."""
    vec = [0] * 7
    vec[dow] = 1
    return vec


def aggregate_daily_usage(events: list[dict]) -> list[dict]:
    """
    Aggregate raw usage events into daily summaries.
    Returns sorted list of {date, total_consumed, dow, is_weekend, days_since_start}.
    """
    daily: dict[str, float] = defaultdict(float)
    for ev in events:
        ts = ev.get("timestamp", "")
        date_str = ts[:10]  # YYYY-MM-DD
        daily[date_str] += abs(ev.get("qty_change", 0))

    if not daily:
        return []

    sorted_dates = sorted(daily.keys())
    start_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d")
    result = []
    for date_str in sorted_dates:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dow = dt.weekday()
        result.append(
            {
                "date": date_str,
                "total_consumed": daily[date_str],
                "dow": dow,
                "is_weekend": dow >= 5,
                "days_since_start": (dt - start_date).days,
            }
        )
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Forecast Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def forecast_burn_rate(
    item_id: str,
    events: Optional[list[dict]] = None,
    current_stock: Optional[float] = None,
) -> dict:
    """
    Predict when an item will run out using Linear Regression
    with day-of-week seasonality features.
    """
    import database as db

    # Fetch data if not provided (for testing, data can be injected)
    if events is None:
        events = await db.get_usage_events(item_id, days=30)
    if current_stock is None:
        current_stock = await db.get_current_quantity(item_id)

    if len(events) < 7:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": f"Need at least 7 days of data, have {len(events)}",
            "days_of_supply": None,
            "daily_burn_rate": 0,
            "weekend_multiplier": 1.0,
            "predicted_runout_date": None,
            "r_squared": 0,
            "data_points_used": len(events),
        }

    daily_usage = aggregate_daily_usage(events)

    if not daily_usage:
        return {
            "status": "NO_DATA",
            "message": "No usage data found",
            "days_of_supply": None,
            "daily_burn_rate": 0,
            "weekend_multiplier": 1.0,
            "predicted_runout_date": None,
            "r_squared": 0,
            "data_points_used": 0,
        }

    # Build feature matrix
    X = []
    y = []
    for day_data in daily_usage:
        features = [
            day_data["days_since_start"],
            int(day_data["is_weekend"]),
            *one_hot_day_of_week(day_data["dow"]),
        ]
        X.append(features)
        y.append(day_data["total_consumed"])

    X_arr = np.array(X)
    y_arr = np.array(y)

    # Fit model
    model = LinearRegression()
    model.fit(X_arr, y_arr)
    r_squared = model.score(X_arr, y_arr)

    # Calculate weekend multiplier with NaN guard
    weekday_values = [
        y_arr[i] for i in range(len(y_arr)) if not daily_usage[i]["is_weekend"]
    ]
    weekend_values = [
        y_arr[i] for i in range(len(y_arr)) if daily_usage[i]["is_weekend"]
    ]

    if not weekend_values:
        weekend_multiplier = 1.0
    else:
        weekday_avg = np.mean(weekday_values) if weekday_values else 0.01
        weekend_avg = np.mean(weekend_values)
        weekend_multiplier = round(weekend_avg / max(weekday_avg, 0.01), 2)

    # Predict future consumption — step-forward simulation
    # Use simulated date if available (dev mode)
    try:
        from dev_mode import get_current_date
        _now = await get_current_date()
    except Exception:
        _now = datetime.now()

    remaining = current_stock
    predict_day = len(daily_usage)
    runout_date = _now
    max_horizon = 365

    while remaining > 0 and predict_day < max_horizon:
        future_date = _now + timedelta(
            days=predict_day - len(daily_usage) + 1
        )
        dow = future_date.weekday()
        is_wkend = 1 if dow >= 5 else 0
        features = [predict_day, is_wkend, *one_hot_day_of_week(dow)]
        predicted_usage = max(0, model.predict([features])[0])
        remaining -= predicted_usage
        runout_date = future_date
        predict_day += 1

    daily_burn_rate = float(np.mean(y_arr))
    days_of_supply = (
        current_stock / daily_burn_rate if daily_burn_rate > 0 else float("inf")
    )

    return {
        "status": "OK",
        "current_stock": current_stock,
        "daily_burn_rate": round(daily_burn_rate, 2),
        "weekend_multiplier": weekend_multiplier,
        "days_of_supply": round(days_of_supply, 1),
        "predicted_runout_date": runout_date.strftime("%Y-%m-%d"),
        "r_squared": round(r_squared, 3),
        "data_points_used": len(y_arr),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Scheduler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def update_all_forecasts() -> int:
    """Recalculate forecasts for all active inventory items. Returns count."""
    import database as db

    items = await db.get_all_active_items()
    count = 0
    for item in items:
        try:
            forecast = await forecast_burn_rate(item["id"])
            if forecast["status"] == "OK":
                await db.upsert_forecast(item["id"], forecast)
                count += 1

                # Auto-trigger triage if running low
                if (
                    forecast.get("days_of_supply") is not None
                    and forecast["days_of_supply"] <= 3
                ):
                    await db.update_inventory_item(
                        item["id"], status="EXPIRING_SOON"
                    )
        except Exception as exc:
            logger.warning("Forecast failed for %s: %s", item["id"], exc)

    return count


async def forecast_scheduler(interval_seconds: int = 3600) -> None:
    """
    Periodic forecast updater.
    Launched as a background asyncio task on FastAPI startup.
    Runs immediately on first call, then every interval_seconds.
    """
    import database as db

    first_run = True
    while True:
        if first_run:
            await asyncio.sleep(5)  # brief delay for DB readiness
            first_run = False
        else:
            await asyncio.sleep(interval_seconds)
        try:
            count = await update_all_forecasts()
            await db.log_audit(
                "FORECAST_SCHEDULED",
                details={"updated": count, "interval": interval_seconds},
            )
            logger.info("Scheduled forecast complete: %d items updated", count)
        except Exception as exc:
            logger.error("Scheduled forecast failed: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Test Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_mock_events(
    item_id: str, daily_rate: float, days: int
) -> list[dict]:
    """Generate mock usage events for testing."""
    events = []
    base = datetime.now() - timedelta(days=days)
    for d in range(days):
        dt = base + timedelta(days=d)
        events.append(
            {
                "item_id": item_id,
                "timestamp": dt.strftime("%Y-%m-%d 12:00:00"),
                "action_type": "USE",
                "qty_change": -daily_rate,
                "day_of_week": dt.weekday(),
                "is_weekend": 1 if dt.weekday() >= 5 else 0,
                "notes": "Mock event",
            }
        )
    return events


def generate_mock_events_with_weekend_spike(
    item_id: str,
    weekday_rate: float,
    weekend_rate: float,
    days: int,
) -> list[dict]:
    """Generate mock events with different weekend consumption for testing."""
    events = []
    base = datetime.now() - timedelta(days=days)
    for d in range(days):
        dt = base + timedelta(days=d)
        is_wkend = dt.weekday() >= 5
        rate = weekend_rate if is_wkend else weekday_rate
        events.append(
            {
                "item_id": item_id,
                "timestamp": dt.strftime("%Y-%m-%d 12:00:00"),
                "action_type": "USE",
                "qty_change": -rate,
                "day_of_week": dt.weekday(),
                "is_weekend": 1 if is_wkend else 0,
                "notes": "Weekend spike" if is_wkend else "Weekday",
            }
        )
    return events
