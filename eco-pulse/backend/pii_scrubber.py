"""
Eco-Pulse V3.0 — PII Scrubber
Synchronous regex-based PII removal (no async I/O).
Two scrubbing stages:
  1. Pre-AI  — text input only (before sending to Gemini)
  2. Pre-DB  — ALL extracted fields from any input mode (before DB storage)
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("ecopulse.pii")

# Ordered list of (pattern, replacement) pairs
PII_PATTERNS: list[tuple[str, str]] = [
    # Credit card numbers  (with spaces, dashes, or no separator)
    (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CARD]"),
    # Phone numbers  (US format variants)
    (
        r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[REDACTED_PHONE]",
    ),
    # Email addresses
    (
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[REDACTED_EMAIL]",
    ),
    # SSN  (US)
    (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "[REDACTED_SSN]"),
]


def scrub_pii(text: str) -> str:
    """
    Synchronous PII scrubber.
    Removes PII patterns from text via regex.
    Used pre-AI for text input and pre-DB for all extracted fields.
    """
    if not text:
        return text

    redaction_count = 0
    scrubbed = text

    for pattern, replacement in PII_PATTERNS:
        matches = re.findall(pattern, scrubbed)
        if matches:
            redaction_count += len(matches)
            scrubbed = re.sub(pattern, replacement, scrubbed)

    if redaction_count > 0:
        logger.info("PII_SCRUBBED: %d redaction(s) applied", redaction_count)

    return scrubbed


def scrub_extracted_fields(item: dict) -> dict:
    """
    Scrub PII from all text fields of an extracted item before DB storage.
    Applied to ALL input modes (image, voice, text) after Gemini extraction.
    """
    text_fields = ["item_name", "raw_input_text", "source_description"]
    for field in text_fields:
        if field in item and isinstance(item[field], str):
            item[field] = scrub_pii(item[field])
    return item
