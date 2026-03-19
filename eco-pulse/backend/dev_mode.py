"""
Eco-Pulse V3.0 — Developer Mode
Time simulation via system_config table so both Python and Grafana
read the same simulated date.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("ecopulse.devmode")


async def get_current_date() -> datetime:
    """
    Returns the current date, reading the simulated date from the
    system_config table if one is set. Falls back to real current date.
    """
    import database as db

    simulated = await db.get_config("simulated_date")
    if simulated:
        return datetime.fromisoformat(simulated)
    return datetime.now()


async def advance_time(days: int) -> str:
    """
    Simulate time passing by N days.
    - Persists the new simulated date to system_config (Grafana reads it too)
    - Recalculates expiry status for all items
    - Triggers triage for newly-expiring items
    - Regenerates forecasts
    Returns the new simulated date as ISO string.
    """
    import database as db

    current = await get_current_date()
    new_date = current + timedelta(days=days)
    new_date_str = new_date.date().isoformat()

    # Persist to system_config — Grafana queries will pick this up
    await db.set_config("simulated_date", new_date_str)

    # Update expiry statuses
    await recalculate_expiry_status(new_date_str)

    # Auto-trigger triage for items now in the danger zone
    try:
        from predictive_math import update_all_forecasts

        await update_all_forecasts()
    except Exception as exc:
        logger.warning("Forecast update during time advance failed: %s", exc)

    await db.log_audit(
        "DEV_TIME_ADVANCE",
        details={"days_advanced": days, "new_simulated_date": new_date_str},
    )

    logger.info("Time advanced by %d days → %s", days, new_date_str)
    return new_date_str


async def recalculate_expiry_status(reference_date: Optional[str] = None) -> int:
    """
    Recalculate the status of all inventory items based on expiry dates.
    Returns the number of items whose status changed.
    """
    import database as db

    if reference_date is None:
        current = await get_current_date()
        reference_date = current.date().isoformat()

    items = await db.get_all_active_items()
    changed = 0
    for item in items:
        if not item.get("expiry_date"):
            continue

        try:
            exp = datetime.fromisoformat(item["expiry_date"])
            ref = datetime.fromisoformat(reference_date)
            days_left = (exp - ref).days

            if days_left < 0:
                new_status = "EXPIRED"
            elif days_left <= 3:
                new_status = "EXPIRING_SOON"
            else:
                new_status = "ACTIVE"

            if new_status != item["status"]:
                await db.update_inventory_item(item["id"], status=new_status)
                changed += 1
        except (ValueError, TypeError):
            continue

    return changed


async def reset_simulated_date() -> None:
    """Clear the simulated date, reverting to real time."""
    import database as db

    await db.set_config("simulated_date", "")
    logger.info("Simulated date cleared — using real time")
