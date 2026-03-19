"""
Eco-Pulse V3.0 — Configuration Management
Uses pydantic-settings for type-safe environment variable management.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # ── AI Configuration ──────────────────────────────────
    gemini_api_key: str = Field(
        default="",
        description="Google AI Studio API key for Gemini 2.5 Flash",
    )
    model_name: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use",
    )
    confidence_threshold: float = Field(
        default=0.85,
        description="Minimum confidence to accept AI extraction (0.0–1.0)",
    )
    llm_timeout_seconds: int = Field(
        default=60,
        description="Maximum seconds to wait for LLM response",
    )

    # ── Database ──────────────────────────────────────────
    database_path: str = Field(
        default="/data/ecopulse.db",
        description="Path to the SQLite database file",
    )

    # ── Application ───────────────────────────────────────
    dev_mode: bool = Field(
        default=False,
        description="Enable developer mode (time simulation, extra commands)",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # ── Grafana ───────────────────────────────────────────
    grafana_url: str = Field(
        default="http://localhost:3000",
        description="Grafana URL for dashboard links",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton settings instance
settings = Settings()


def validate_settings() -> None:
    """
    Validate critical settings at startup. Fail fast with a clear, helpful
    error message if the API key is missing or still using the placeholder.
    """
    placeholder = "your-google-ai-studio-api-key"
    if not settings.gemini_api_key or settings.gemini_api_key == placeholder:
        from rich.console import Console
        from rich.panel import Panel

        console = Console(stderr=True)
        console.print(
            Panel(
                "[bold red]GEMINI_API_KEY is not configured.[/bold red]\n\n"
                "1. Get a free key at: [link=https://ai.google.dev]https://ai.google.dev[/link]\n"
                "2. Copy the example env file:  [cyan]cp .env.example .env[/cyan]\n"
                "3. Set your key:  [cyan]GEMINI_API_KEY=your-key-here[/cyan]\n\n"
                "[dim]AI features will be unavailable until a valid key is set.\n"
                "Fallback paths will handle requests gracefully.[/dim]",
                title="⚠️  Configuration Error",
                border_style="red",
            )
        )
        raise SystemExit(1)
