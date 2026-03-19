"""
Eco-Pulse V3.0 — Timeout & Rate Limit Tests
5 tests covering F3 (timeout → human review) and F4 (rate limit → backoff).
"""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

_parent = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_parent, "backend"))  # local dev
sys.path.insert(0, _parent)                            # Docker

from unittest.mock import AsyncMock, MagicMock, patch

from schemas import ExtractionResult, ExtractedItem, ItemCategory, ItemUnit


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  F3: Timeout → Human Review (No Auto-Discount)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_llm_timeout_routes_to_human_review(test_db):
    """F3: LLM times out → item routed to human review, NO auto-discount."""

    async def mock_extract_timeout(text_input):
        raise asyncio.TimeoutError()

    with patch("ai_service.extract_from_text", side_effect=mock_extract_timeout):
        with patch("config.settings") as mock_settings:
            mock_settings.llm_timeout_seconds = 0
            mock_settings.model_name = "gemini-2.5-flash"
            mock_settings.confidence_threshold = 0.85
            mock_settings.gemini_api_key = "test"

            from ai_service import process_input

            result = await process_input("10 apples", input_method="TEXT")

            assert result.items_sent_to_review >= 1
            assert "TIMEOUT" in result.review_reasons or result.fallback_triggered == "TIMEOUT"
            # Crucially: no auto-discount
            assert result.fallback_triggered != "AUTO_DISCOUNT_50"


@pytest.mark.asyncio
async def test_timeout_creates_audit_trail(test_db):
    """Verify audit log entry is created on timeout."""

    async def mock_extract_timeout(text_input):
        raise asyncio.TimeoutError()

    with patch("ai_service.extract_from_text", side_effect=mock_extract_timeout):
        with patch("config.settings") as mock_settings:
            mock_settings.llm_timeout_seconds = 0
            mock_settings.model_name = "gemini-2.5-flash"
            mock_settings.confidence_threshold = 0.85
            mock_settings.gemini_api_key = "test"

            from ai_service import process_input

            await process_input("10 apples", input_method="TEXT")

            # Check audit log
            logs = await test_db.get_audit_logs(event_type="AI_FALLBACK")
            assert len(logs) >= 1
            last_log = logs[0]
            assert last_log["severity"] in ("WARN", "ERROR")
            assert "TIMEOUT" in (last_log.get("details") or "")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  F4: Rate Limit → Backoff → Retry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_rate_limit_waits_and_retries(test_db):
    """F4: Rate limited → wait → retry succeeds."""
    good_result = ExtractionResult(
        items=[
            ExtractedItem(
                item_name="whole milk",
                quantity=10,
                unit=ItemUnit.LITERS,
                category=ItemCategory.MILK_CREAM,
                confidence_score=0.92,
                expiry_date="2026-03-25",
                raw_input_text="10L whole milk",
            )
        ],
        source_description="Success after rate limit",
    )

    call_count = 0
    notifications: list[str] = []

    async def mock_call_gemini(contents, schema):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("ResourceExhausted: 429 Rate limit exceeded")
        return good_result.model_dump_json()

    with patch("ai_service.call_gemini", side_effect=mock_call_gemini):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from ai_service import call_gemini_with_rate_limit_handling

            result = await call_gemini_with_rate_limit_handling(
                contents=["test"],
                schema={},
                notify_callback=lambda msg: notifications.append(msg),
                max_retries=3,
            )

            assert len(result.items) == 1
            assert any("rate limit" in n.lower() for n in notifications)


@pytest.mark.asyncio
async def test_rate_limit_retry_exhausted(test_db):
    """F4: All retries fail → raises exception for caller to handle."""

    async def mock_always_rate_limited(contents, schema):
        raise Exception("ResourceExhausted: 429 Rate limit exceeded")

    notifications: list[str] = []

    with patch("ai_service.call_gemini", side_effect=mock_always_rate_limited):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from ai_service import call_gemini_with_rate_limit_handling

            with pytest.raises(Exception):
                await call_gemini_with_rate_limit_handling(
                    contents=["test"],
                    schema={},
                    notify_callback=lambda msg: notifications.append(msg),
                    max_retries=3,
                )

            # Should have notified about retries
            assert len(notifications) >= 1


@pytest.mark.asyncio
async def test_api_error_notifies_and_raises(test_db):
    """F4b: API connection error → user notified → exception raised."""
    notifications: list[str] = []

    async def mock_connection_error(contents, schema):
        raise ConnectionError("API unreachable")

    with patch("ai_service.call_gemini", side_effect=mock_connection_error):
        from ai_service import call_gemini_with_rate_limit_handling

        with pytest.raises(ConnectionError):
            await call_gemini_with_rate_limit_handling(
                contents=["test"],
                schema={},
                notify_callback=lambda msg: notifications.append(msg),
            )

        assert any("connection failed" in n.lower() or "error" in n.lower() for n in notifications)
