"""
Eco-Pulse V3.0 — CLI Interface
Primary demo surface built with Typer + Rich.
Run via:  python -m cli --help
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import webbrowser
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ── Ensure backend is importable ─────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

console = Console()
app = typer.Typer(
    name="eco-pulse",
    help="🌍 Eco-Pulse V3.0 — Zero-Waste Inventory Engine",
    add_completion=False,
    rich_markup_mode="rich",
)


# ── Async runner helper ──────────────────────────────────
def _run(coro):
    """Run an async coroutine from sync Typer commands."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # If already in an async context, use the existing loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


async def _ensure_db():
    """Ensure the database is initialised before CLI commands."""
    import database as db
    from config import settings

    if db._engine is None:
        await db.init_db(settings.database_path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INGEST Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.command()
def ingest(
    image: Optional[str] = typer.Option(None, "--image", "-i", help="Path to receipt/shelf image"),
    voice: bool = typer.Option(False, "--voice", "-v", help="Record or upload voice input"),
    voice_file: Optional[str] = typer.Option(None, "--file", "-f", help="Pre-recorded audio file (for Docker/demo)"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Natural language text input"),
    csv_file: Optional[str] = typer.Option(None, "--csv", help="Bulk CSV import file"),
    multiplier: float = typer.Option(1.0, "--multiplier", "-m", help="Quantity multiplier for image ingestion (e.g. 2.0 doubles all quantities)"),
):
    """Add items to inventory via image, voice, text, or CSV."""

    async def _do_ingest():
        await _ensure_db()
        from ai_service import process_input
        from config import settings

        input_method: str
        input_data: str

        if image:
            input_method = "IMAGE"
            input_data = image
            mult_info = f" × {multiplier}x" if multiplier != 1.0 else ""
            _print_header("🧾 Receipt Processing", f"Input: {os.path.basename(image)} (IMAGE){mult_info}")
        elif voice or voice_file:
            input_method = "VOICE"
            if voice_file:
                input_data = voice_file
            else:
                # Try live recording
                try:
                    input_data = _record_voice()
                except Exception:
                    console.print("[yellow]⚠️  No audio hardware detected. Please provide a file path:[/yellow]")
                    input_data = typer.prompt("Audio file path")
            _print_header("🎙️ Voice Processing", f"Input: {os.path.basename(input_data)} (VOICE)")
        elif text:
            input_method = "TEXT"
            input_data = text
            _print_header("✏️ Text Processing", f"Input: \"{text[:60]}…\" (TEXT)")
        elif csv_file:
            # CSV bulk import
            import csv as csv_mod
            import database as db

            _print_header("📦 CSV Import", f"File: {os.path.basename(csv_file)}")
            count = 0
            with open(csv_file, "r") as f:
                reader = csv_mod.DictReader(f)
                for row in reader:
                    await db.insert_inventory_item(
                        item_name=row.get("item_name", "unknown"),
                        category=row.get("category", "Other"),
                        quantity=float(row.get("quantity", 0)),
                        unit=row.get("unit", "units"),
                        expiry_date=row.get("expiry_date"),
                        co2_per_unit_kg=float(row.get("co2_per_unit_kg", 0)),
                        confidence_score=1.0,
                        input_method="CSV_IMPORT",
                    )
                    count += 1
            console.print(f"  ✅  {count} items imported from CSV")
            return
        else:
            console.print("[red]Please specify --image, --voice, --text, or --csv[/red]")
            raise typer.Exit(1)

        # Process via AI pipeline
        notifications: list[str] = []

        def notify(msg: str):
            notifications.append(msg)
            console.print(f"  {msg}")

        try:
            result = await process_input(input_data, input_method, notify_callback=notify, multiplier=multiplier if input_method == "IMAGE" else 1.0)
            _print_ingestion_result(result, input_method)
        except Exception as exc:
            console.print(f"[red]❌ Processing failed: {exc}[/red]")

    _run(_do_ingest())


def _record_voice() -> str:
    """Record audio from microphone. Returns path to WAV file."""
    import tempfile

    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    sample_rate = 16000
    console.print("[cyan]🎙️  Press Enter to start recording...[/cyan]")
    input()
    console.print("[green]Recording... Press Enter to stop.[/green]")

    frames: list = []
    recording = True

    def callback(indata, frame_count, time_info, status):
        if recording:
            frames.append(indata.copy())

    stream = sd.InputStream(samplerate=sample_rate, channels=1, callback=callback)
    stream.start()
    input()
    recording = False
    stream.stop()

    audio = np.concatenate(frames)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, sample_rate)
    return tmp.name


def _print_header(title: str, subtitle: str):
    """Print a styled header panel."""
    from config import settings

    panel_text = (
        f"{subtitle}\n"
        f"Model:    {settings.model_name}\n"
        f"Status:   ⏳ Processing…"
    )
    console.print(Panel(panel_text, title=title, border_style="cyan"))


def _print_ingestion_result(result, input_method: str):
    """Print a beautiful ingestion result table."""
    from config import settings

    # Summary
    status_icon = "✅" if result.items_added_to_inventory > 0 else "⚠️"
    summary = (
        f"Status:   {status_icon} Processing Complete\n"
        f"Model:    {settings.model_name}"
    )
    if result.fallback_triggered:
        summary += f"\nFallback: ⚠️  {result.fallback_triggered}"

    console.print()

    if result.items_sent_to_review > 0:
        console.print(
            f"  ⚠️  {result.items_sent_to_review} item(s) routed to "
            f"[yellow]PENDING_HUMAN_REVIEW[/yellow] "
            f"({', '.join(result.review_reasons)})"
        )
    if result.items_added_to_inventory > 0:
        console.print(
            f"  ✅  {result.items_added_to_inventory} item(s) added to "
            f"[green]active inventory[/green]"
        )
    if result.total_carbon_footprint > 0:
        console.print(
            f"  🌍  Total carbon footprint: "
            f"[bold]{result.total_carbon_footprint:.1f}[/bold] kg CO₂"
        )
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INVENTORY Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

inventory_app = typer.Typer(help="📦 View and manage inventory")
app.add_typer(inventory_app, name="inventory")


@inventory_app.command("list")
def inventory_list(
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    search: Optional[str] = typer.Option(None, "--search", "-q"),
):
    """List all items with optional filters."""

    async def _do():
        await _ensure_db()
        import database as db

        items = await db.get_all_items(category=category, status=status, search=search)
        _print_inventory_table(items)

    _run(_do())


@inventory_app.command("search")
def inventory_search(query: str = typer.Argument(...)):
    """Search inventory by name or category."""

    async def _do():
        await _ensure_db()
        import database as db

        items = await db.search_items(query)
        _print_inventory_table(items)

    _run(_do())


@inventory_app.command("update")
def inventory_update(
    item_id: str = typer.Argument(...),
    qty: Optional[float] = typer.Option(None, "--qty"),
    status: Optional[str] = typer.Option(None, "--status"),
):
    """Update an item's quantity or status."""

    async def _do():
        await _ensure_db()
        import database as db

        item = await db.get_item(item_id)
        if not item:
            console.print(f"[red]Item {item_id} not found[/red]")
            return
        updates = {}
        if qty is not None:
            updates["quantity"] = qty
        if status is not None:
            updates["status"] = status
        if updates:
            await db.update_inventory_item(item_id, **updates)
            console.print(f"  ✅  Updated [cyan]{item['item_name']}[/cyan]")
        else:
            console.print("[yellow]No changes specified[/yellow]")

    _run(_do())


@inventory_app.command("review")
def inventory_review():
    """View & approve pending items."""

    async def _do():
        await _ensure_db()
        import database as db

        reviews = await db.get_pending_reviews()
        if not reviews:
            console.print("  ✅  No items pending review")
            return

        table = Table(
            title="👁️  Pending Human Review",
            box=box.ROUNDED,
            title_style="bold magenta",
        )
        table.add_column("#", style="bold", max_width=4)
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Suggested Item", style="cyan")
        table.add_column("Qty", justify="right")
        table.add_column("Confidence", justify="center")
        table.add_column("Reason", style="yellow")
        table.add_column("Created", style="dim")

        for idx, r in enumerate(reviews, 1):
            conf = f"{r['confidence_score']*100:.0f}%" if r.get("confidence_score") else "—"
            table.add_row(
                str(idx),
                r["id"][:8],
                r.get("suggested_item_name") or "—",
                f"{r.get('suggested_quantity', 0):.1f}",
                conf,
                r.get("failure_reason", "—"),
                r.get("created_at", "")[:16],
            )

        console.print(table)

        # Interactive approve/reject
        action = typer.prompt(
            "Enter row # or review ID to approve (or 'skip' to exit)", default="skip"
        )
        if action != "skip":
            # Accept row number (1-based) or raw UUID
            review_id = action
            if action.isdigit():
                idx = int(action) - 1
                if 0 <= idx < len(reviews):
                    review_id = reviews[idx]["id"]
                else:
                    console.print("[yellow]Invalid row number[/yellow]")
                    return
            item_id = await db.approve_review(review_id)
            if item_id:
                console.print(f"  ✅  Approved → added to inventory (ID: {item_id[:8]})")
            else:
                console.print("[yellow]Review not found or already processed[/yellow]")

    _run(_do())


def _print_inventory_table(items: list[dict]):
    """Print a beautiful inventory table."""
    if not items:
        console.print("  📦  Inventory is empty")
        return

    table = Table(
        title="📦 Inventory",
        box=box.ROUNDED,
        title_style="bold green",
    )
    table.add_column("Item", style="cyan", min_width=16)
    table.add_column("Category", style="dim")
    table.add_column("Qty", justify="right", style="bold")
    table.add_column("Unit")
    table.add_column("Expiry", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("CO₂/unit", justify="right", style="dim")
    table.add_column("Confidence", justify="center")

    from datetime import datetime

    for item in items:
        # Status indicator
        status = item.get("status", "ACTIVE")
        exp = item.get("expiry_date", "")
        if exp:
            try:
                days_left = (datetime.fromisoformat(exp) - datetime.now()).days
                if days_left <= 2:
                    status_str = "🔴 URGENT"
                elif days_left <= 7:
                    status_str = "🟡 WARNING"
                else:
                    status_str = "🟢 SAFE"
            except (ValueError, TypeError):
                status_str = status
        else:
            status_str = "🟢 N/A"

        conf = item.get("confidence_score")
        conf_str = f"{conf*100:.0f}%" if conf else "—"

        table.add_row(
            item.get("item_name", "?"),
            item.get("category", "?"),
            f"{item.get('quantity', 0):.1f}",
            item.get("unit", "?"),
            exp[:10] if exp else "—",
            status_str,
            f"{item.get('co2_per_unit_kg', 0):.1f}",
            conf_str,
        )

    console.print(table)
    console.print(f"  Total: {len(items)} item(s)\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TRIAGE Command
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.command()
def triage(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview actions without DB writes"),
):
    """🚨 Show expiring items and generate AI recipes."""

    async def _do():
        await _ensure_db()
        from datetime import datetime

        import database as db
        from dev_mode import get_current_date

        current = await get_current_date()
        expiring_3 = await db.get_items_expiring_within(days=3)
        expiring_7 = await db.get_items_expiring_within(days=7)

        console.print(
            Panel(
                f"Items Expiring Within 7 Days: {len(expiring_7)}\n"
                f"Items Expiring Within 3 Days: {len(expiring_3)}  "
                + ("← AI TRIAGE TRIGGERED" if expiring_3 else ""),
                title="🚨 Expiry Triage (FEFO Order)",
                border_style="red" if expiring_3 else "yellow",
            )
        )

        if expiring_7:
            table = Table(box=box.ROUNDED, title_style="bold red")
            table.add_column("Item", style="cyan")
            table.add_column("Qty", justify="right", style="bold")
            table.add_column("Expires", justify="center")
            table.add_column("Status", justify="center")
            table.add_column("Action Taken")

            for item in expiring_7:
                exp = item.get("expiry_date", "")
                try:
                    days_left = (datetime.fromisoformat(exp) - current).days
                except (ValueError, TypeError):
                    days_left = 99

                if days_left <= 1:
                    indicator = "🔴"
                    status = "URGENT"
                elif days_left <= 3:
                    indicator = "🔴"
                    status = "URGENT"
                else:
                    indicator = "🟡"
                    status = "WARNING"

                action = "Monitoring" if days_left > 3 else "🍳 AI Triage"
                table.add_row(
                    f"{indicator} {item['item_name']}",
                    f"{item['quantity']:.0f} {item.get('unit', '')}",
                    f"{days_left} days" if days_left >= 0 else "EXPIRED",
                    status,
                    action,
                )

            console.print(table)

        # Generate recipes for urgent items
        if expiring_3 and not dry_run:
            console.print()
            try:
                from ai_service import generate_recipes_with_ai

                with console.status("[bold green]Generating AI recipes…[/bold green]"):
                    recipe_response = await generate_recipes_with_ai(expiring_3)

                if recipe_response.recipes:
                    # Build CO2 lookup from expiring items
                    co2_lookup = {item["item_name"].lower(): item.get("co2_per_unit_kg", 0) for item in expiring_3}
                    recipe_panel = ""
                    for i, recipe in enumerate(recipe_response.recipes, 1):
                        ingredients_str = ", ".join(recipe.ingredients_used)
                        qty_parts = [f"{name}: {qty}" for name, qty in recipe.quantities_used.items()]
                        qty_str = ", ".join(qty_parts) if qty_parts else ingredients_str

                        # Discount line
                        discount_line = ""
                        if recipe.discount_percent and recipe.suggested_price:
                            discount_line = (
                                f"   💰 [bold yellow]MENU DEAL:[/bold yellow] "
                                f"[dim]${recipe.original_price:.2f}[/dim] → "
                                f"[bold green]${recipe.suggested_price:.2f}[/bold green] "
                                f"([red]{recipe.discount_percent}% OFF[/red])\n"
                            )

                        recipe_panel += (
                            f"{i}. 🥄 [bold]{recipe.title}[/bold] "
                            f"(uses {qty_str})\n"
                            f"   Servings: {recipe.estimated_servings}\n"
                            f"{discount_line}"
                            f"   {recipe.instructions[:120]}…\n\n"
                        )

                        # CO2 saved = quantity actually diverted from waste × co2 rate
                        co2_saved = sum(
                            co2_lookup.get(name.lower(), 0) * qty
                            for name, qty in recipe.quantities_used.items()
                        )

                        # Persist recipe
                        await db.insert_recipe(
                            title=recipe.title,
                            ingredients_used=recipe.ingredients_used,
                            instructions=recipe.instructions,
                            estimated_servings=recipe.estimated_servings,
                            co2_saved_kg=round(co2_saved, 2),
                            original_price=recipe.original_price,
                            suggested_price=recipe.suggested_price,
                            discount_percent=recipe.discount_percent,
                            ai_generated=True,
                        )

                    console.print(
                        Panel(
                            recipe_panel.rstrip(),
                            title="🍳 AI-Generated \"Save-It\" Recipes & 💰 Menu Deals",
                            border_style="green",
                        )
                    )
            except Exception as exc:
                console.print(f"[yellow]⚠️  Recipe generation failed: {exc}[/yellow]")
        elif not expiring_7:
            console.print("  ✅  No items expiring within 7 days")

    _run(_do())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FORECAST Command
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.command()
def forecast(
    item_id: Optional[str] = typer.Option(None, "--item-id", "-id"),
    refresh: bool = typer.Option(False, "--refresh", help="Recalculate all forecasts"),
):
    """📈 Burn-rate predictions."""

    async def _do():
        await _ensure_db()
        from predictive_math import forecast_burn_rate, update_all_forecasts

        if refresh:
            with console.status("[bold green]Updating forecasts…[/bold green]"):
                count = await update_all_forecasts()
            console.print(f"  ✅  Updated {count} forecast(s)")
            return

        if item_id:
            result = await forecast_burn_rate(item_id)
            if result["status"] == "OK":
                import database as db
                await db.upsert_forecast(item_id, result)
            _print_forecast_detail(result, item_id)
        else:
            import database as db

            items = await db.get_all_active_items()
            table = Table(
                title="📈 Burn-Rate Forecasts",
                box=box.ROUNDED,
                title_style="bold blue",
            )
            table.add_column("Item", style="cyan")
            table.add_column("Stock", justify="right")
            table.add_column("Burn/Day", justify="right")
            table.add_column("Weekend ×", justify="center")
            table.add_column("Days Left", justify="right", style="bold")
            table.add_column("Run-Out", justify="center")
            table.add_column("Expiry In", justify="right")
            table.add_column("Status", justify="center")
            table.add_column("R²", justify="right", style="dim")

            for item in items:
                result = await forecast_burn_rate(item["id"])
                # Persist to DB so the API endpoint stays current
                if result["status"] == "OK":
                    await db.upsert_forecast(item["id"], result)
                if result["status"] != "OK":
                    table.add_row(
                        item["item_name"],
                        f"{item['quantity']:.0f}",
                        "—",
                        "—",
                        "Insufficient data",
                        "—",
                        "—",
                        "—",
                        "—",
                    )
                    continue

                days = result.get("days_of_supply")
                days_str = f"{days:.1f}" if days and days < 999 else "∞"
                style = ""
                if days and days <= 3:
                    style = "bold red"
                elif days and days <= 7:
                    style = "yellow"

                # Compute days till expiry and stock status
                from datetime import datetime as _dt
                expiry = item.get("expiry_date")
                runout = result.get("predicted_runout_date")
                sim_date_str = await db.get_config("simulated_date")
                today_str = sim_date_str or _dt.now().strftime("%Y-%m-%d")
                if expiry:
                    dte = (_dt.strptime(expiry, "%Y-%m-%d") - _dt.strptime(today_str, "%Y-%m-%d")).days
                    dte_str = str(dte)
                else:
                    dte = None
                    dte_str = "—"
                # Status: compare runout vs expiry
                if expiry is None:
                    stock_status = "Understocked" if days and days <= 7 else "Well Stocked"
                elif runout and expiry < runout:
                    stock_status = "Overstocked"
                elif runout and expiry:
                    dte_int = (_dt.strptime(expiry, "%Y-%m-%d") - _dt.strptime(today_str, "%Y-%m-%d")).days
                    dtr_int = (_dt.strptime(runout, "%Y-%m-%d") - _dt.strptime(today_str, "%Y-%m-%d")).days
                    stock_status = "Well Stocked" if dte_int == dtr_int else "Understocked"
                else:
                    stock_status = "—"
                status_style = {"Overstocked": "bold blue", "Well Stocked": "bold green", "Understocked": "bold red"}.get(stock_status, "")

                table.add_row(
                    item["item_name"],
                    f"{result['current_stock']:.0f} {item.get('unit', '')}",
                    f"{result['daily_burn_rate']:.1f}",
                    f"{result['weekend_multiplier']:.1f}×",
                    Text(days_str, style=style),
                    result.get("predicted_runout_date", "—"),
                    dte_str,
                    Text(stock_status, style=status_style),
                    f"{result['r_squared']:.2f}",
                )

            console.print(table)

    _run(_do())


def _print_forecast_detail(result: dict, item_id: str):
    """Print a detailed forecast panel for a single item."""
    if result["status"] != "OK":
        console.print(f"  ⚠️  {result.get('message', 'Insufficient data')}")
        return

    days = result.get("days_of_supply")
    warning = ""
    if days and days <= 3:
        warning = "\n⚠️  REORDER RECOMMENDED"

    console.print(
        Panel(
            f"Current Stock:       {result['current_stock']}\n"
            f"Daily Burn Rate:     {result['daily_burn_rate']}/day\n"
            f"Weekend Multiplier:  {result['weekend_multiplier']}×\n"
            f"Days of Supply:      {days:.1f}\n"
            f"Predicted Run-Out:   {result.get('predicted_runout_date', '—')}\n"
            f"Model R²:            {result['r_squared']}\n"
            f"Data Points Used:    {result['data_points_used']}"
            + warning,
            title=f"📈 Burn-Rate Forecast: {item_id[:8]}",
            border_style="blue",
        )
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEV Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

dev_app = typer.Typer(help="🛠️ Developer mode commands")
app.add_typer(dev_app, name="dev")


@dev_app.command("advance-time")
def dev_advance_time(days: int = typer.Option(..., "--days", "-d")):
    """⏩ Simulate time passing by N days."""

    async def _do():
        await _ensure_db()
        from dev_mode import advance_time
        import database as db

        new_date = await advance_time(days)
        expiring = await db.get_items_expiring_within(days=3)
        console.print(f"  ⏩ Time advanced by {days} days. Simulated date: [bold]{new_date}[/bold]")
        if expiring:
            console.print(f"  🚨 {len(expiring)} item(s) now in triage zone (< 3 days to expiry)")

    _run(_do())


@dev_app.command("seed-data")
def dev_seed_data():
    """🌱 Load synthetic data into the database."""

    async def _do():
        await _ensure_db()
        try:
            scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
            sys.path.insert(0, scripts_dir)
            parent_dir = os.path.join(os.path.dirname(__file__), "..")
            sys.path.insert(0, parent_dir)

            from scripts.seed_database import seed_all
            from config import settings

            summary = await seed_all(settings.database_path)
            console.print(f"  🌱 Seed complete: {summary}")
        except Exception as exc:
            console.print(f"[red]Seeding failed: {exc}[/red]")

    _run(_do())


@dev_app.command("reset-db")
def dev_reset_db():
    """🗑️ Reset the database (drop all tables and recreate)."""

    async def _do():
        await _ensure_db()
        import database as db

        confirm = typer.confirm("⚠️  This will DELETE ALL data. Continue?", default=False)
        if confirm:
            await db.reset_database()
            console.print("  🗑️ Database reset complete")

    _run(_do())


@dev_app.command("force-timeout")
def dev_force_timeout():
    """⏱️ Force an AI timeout to demonstrate F3 fallback."""

    async def _do():
        await _ensure_db()
        import database as db
        from config import settings

        # Temporarily set an impossibly short timeout
        original = settings.llm_timeout_seconds
        settings.llm_timeout_seconds = 0

        console.print("  ⏱️  Forcing AI timeout (timeout=0s)…")

        try:
            from ai_service import process_input
            result = await process_input(
                "Force timeout test: 10 apples",
                "TEXT",
                notify_callback=lambda msg: console.print(f"  {msg}"),
            )
            console.print(f"  ⚠️  Fallback triggered: {result.fallback_triggered}")
            console.print(f"  📋 Items routed to review: {result.items_sent_to_review}")
        finally:
            settings.llm_timeout_seconds = original

    _run(_do())


@dev_app.command("simulate-rate-limit")
def dev_simulate_rate_limit():
    """🚦 Simulate API rate limiting to demonstrate F4 fallback."""

    async def _do():
        await _ensure_db()
        console.print("  🚦 Simulating rate limit scenario…")
        console.print("  [dim](This would fire rapid AI calls to trigger 429 responses)[/dim]")
        console.print("  ⚠️  Rate limit handling: exponential backoff with 3 retries")
        console.print("  📋 On exhaustion: item routed to human review queue")

        import database as db
        await db.log_audit(
            "AI_RATE_LIMITED",
            severity="WARN",
            details={"reason": "SIMULATED", "note": "Dev mode rate limit simulation"},
        )
        console.print("  ✅  Simulation logged to audit trail")

    _run(_do())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SYSTEM Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.command()
def health():
    """❤️ System health check."""

    async def _do():
        await _ensure_db()
        from config import settings
        from dev_mode import get_current_date
        import database as db

        sim_date = await db.get_config("simulated_date")
        current = await get_current_date()

        table = Table(box=box.ROUNDED, title="❤️ System Health", title_style="bold green")
        table.add_column("Component", style="cyan")
        table.add_column("Status")

        table.add_row("Database", "✅ Connected")
        table.add_row("AI API", "✅ Configured" if settings.gemini_api_key else "⚠️ Not configured")
        table.add_row("Grafana", f"📊 {settings.grafana_url}")
        table.add_row("Dev Mode", "🟢 Enabled" if settings.dev_mode else "⚪ Disabled")
        table.add_row("Current Date", str(current.date()))
        if sim_date:
            table.add_row("Simulated Date", f"⏩ {sim_date}")
        table.add_row("Version", "3.1")

        console.print(table)

    _run(_do())


@app.command()
def dashboard():
    """📊 Open Grafana dashboard in browser."""
    from config import settings

    url = settings.grafana_url
    console.print(f"  📊 Opening Grafana at {url}")
    console.print(f"  🔑 Credentials: admin / ecopulse")
    webbrowser.open(url)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Entry Point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    app()
