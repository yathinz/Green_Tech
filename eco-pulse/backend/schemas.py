"""
Eco-Pulse V3.0 — Pydantic Schemas
All request/response models and Gemini structured-output schemas.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ItemUnit(str, Enum):
    """Canonical base units ONLY — no packaging units like packs/bottles/cans."""

    KG = "kg"
    GRAMS = "g"
    LITERS = "L"
    ML = "mL"
    UNITS = "units"


class ItemCategory(str, Enum):
    """30 granular categories for precise inventory classification."""

    # Dairy
    MILK_CREAM = "Milk & Cream"
    CHEESE = "Cheese"
    YOGURT = "Yogurt"
    BUTTER_SPREADS = "Butter & Spreads"
    EGGS = "Eggs"
    # Produce
    FRESH_FRUIT = "Fresh Fruit"
    FRESH_VEGETABLES = "Fresh Vegetables"
    HERBS_GREENS = "Herbs & Leafy Greens"
    ROOT_VEGETABLES = "Root Vegetables"
    # Meat & Protein
    POULTRY = "Poultry"
    RED_MEAT = "Red Meat"
    SEAFOOD = "Seafood"
    # Bakery
    BREAD = "Bread & Rolls"
    PASTRY = "Pastry & Cakes"
    # Pantry Staples
    GRAINS_RICE = "Grains & Rice"
    PASTA = "Pasta & Noodles"
    COOKING_OIL = "Cooking Oils & Vinegar"
    CONDIMENTS = "Condiments & Sauces"
    SUGAR_SWEETENER = "Sugar & Sweeteners"
    NUTS_SEEDS = "Nuts & Seeds"
    CANNED_PRESERVED = "Canned & Preserved"
    # Beverages
    COFFEE_TEA = "Coffee & Tea"
    JUICE_DRINKS = "Juice & Soft Drinks"
    PLANT_MILK = "Plant-Based Milk"
    # Non-Food
    OFFICE_PAPER = "Office - Paper"
    OFFICE_SUPPLIES = "Office - Supplies"
    CLEANING = "Cleaning Products"
    LAB_CHEMICALS = "Lab Chemicals"
    LAB_EQUIPMENT = "Lab Equipment"
    OTHER = "Other"


class ItemStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    PENDING_TRIAGE = "PENDING_TRIAGE"
    DONATED = "DONATED"
    CONSUMED = "CONSUMED"


class InputMethod(str, Enum):
    IMAGE = "IMAGE"
    VOICE = "VOICE"
    TEXT = "TEXT"
    MANUAL = "MANUAL"
    CSV_IMPORT = "CSV_IMPORT"


class ActionType(str, Enum):
    ADD = "ADD"
    USE = "USE"
    RESTOCK = "RESTOCK"
    WASTE = "WASTE"
    DONATE = "DONATE"
    ADJUST = "ADJUST"


class FailureReason(str, Enum):
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    API_ERROR = "API_ERROR"
    TIMEOUT = "TIMEOUT"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"


class TriageActionType(str, Enum):
    RECIPE_GENERATED = "RECIPE_GENERATED"
    COMMUNITY_MESH = "COMMUNITY_MESH"
    AUTO_DISCOUNT = "AUTO_DISCOUNT"
    DONATION_DRAFTED = "DONATION_DRAFTED"


class AuditEventType(str, Enum):
    AI_CALL = "AI_CALL"
    AI_FALLBACK = "AI_FALLBACK"
    AI_BYPASSED = "AI_BYPASSED"
    AI_RETRY = "AI_RETRY"
    AI_RETRY_SUCCESS = "AI_RETRY_SUCCESS"
    AI_RATE_LIMITED = "AI_RATE_LIMITED"
    INGESTION = "INGESTION"
    ITEM_MERGED = "ITEM_MERGED"
    TRIAGE = "TRIAGE"
    FORECAST = "FORECAST"
    FORECAST_SCHEDULED = "FORECAST_SCHEDULED"
    CARBON_AI_ESTIMATE = "CARBON_AI_ESTIMATE"
    CARBON_LOOKUP_FAILED = "CARBON_LOOKUP_FAILED"
    COMMUNITY_MESH = "COMMUNITY_MESH"
    PII_SCRUBBED = "PII_SCRUBBED"
    DEV_TIME_ADVANCE = "DEV_TIME_ADVANCE"
    ERROR = "ERROR"


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Gemini Structured-Output Schemas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExtractedItem(BaseModel):
    """Schema for a single item extracted by Gemini from any input mode."""

    item_name: str = Field(description="Canonical singular lowercase English name")
    quantity: float = Field(
        description="Quantity converted to base metric unit", ge=0
    )
    unit: ItemUnit = Field(description="Canonical base unit (kg, g, L, mL, or units)")
    raw_input_text: str = Field(
        description="Original text as it appeared in input, for audit",
        default="",
    )
    category: ItemCategory = Field(description="Granular category of the item")
    expiry_date: Optional[str] = Field(
        description="Expiry date in YYYY-MM-DD format, null if not perishable or not specified",
        default=None,
    )
    confidence_score: float = Field(
        description="Confidence in this extraction from 0.0 to 1.0",
        ge=0.0,
        le=1.0,
    )


class ExtractionResult(BaseModel):
    """Top-level response from Gemini extraction across all input modes."""

    items: list[ExtractedItem] = Field(
        description="List of extracted inventory items"
    )
    source_description: str = Field(
        description="Brief description of the source input"
    )


class Recipe(BaseModel):
    """Schema for one AI-generated recipe."""

    title: str = Field(description="Name of the recipe")
    ingredients_used: list[str] = Field(
        description="List of expiring item NAMES used"
    )
    quantities_used: dict[str, float] = Field(
        description="Mapping of ingredient name to quantity used in this recipe",
        default_factory=dict,
    )
    additional_ingredients: list[str] = Field(
        description="Any extra ingredients needed", default_factory=list
    )
    instructions: str = Field(description="Step-by-step cooking instructions")
    estimated_servings: int = Field(description="Number of servings", ge=1)
    difficulty: str = Field(
        description="Easy, Medium, or Hard", default="Easy"
    )
    original_price: float = Field(
        description="Normal menu price for this dish", default=0.0
    )
    suggested_price: float = Field(
        description="Discounted price to sell at", default=0.0
    )
    discount_percent: int = Field(
        description="Discount percentage applied (e.g. 30 for 30%)", default=0
    )


class RecipeResponse(BaseModel):
    """Top-level response from Gemini recipe generation."""

    recipes: list[Recipe] = Field(description="List of generated recipes")
    items_not_used: list[str] = Field(
        description="Expiring items not included in any recipe",
        default_factory=list,
    )


class CarbonEstimate(BaseModel):
    """AI estimate of carbon footprint for unknown items."""

    co2_per_unit_kg: float = Field(description="Estimated kg CO₂ per unit")
    avg_shelf_life_days: Optional[int] = Field(
        description="Estimated shelf life in days", default=None
    )
    source: str = Field(default="AI estimate")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Application-level Response Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class IngestionResponse(BaseModel):
    """Response after processing an ingestion request."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "PROCESSING"
    message: str = ""


class IngestionResult(BaseModel):
    """Final result after ingestion processing completes."""

    items_added_to_inventory: int = 0
    items_sent_to_review: int = 0
    review_reasons: list[str] = Field(default_factory=list)
    total_carbon_footprint: float = 0.0
    retry_count: int = 0
    fallback_triggered: Optional[str] = None
    details: list[dict] = Field(default_factory=list)


class TriageResult(BaseModel):
    """Result of a triage action on an expiring item."""

    action_taken: str
    ai_generated: bool = False
    ai_bypassed: bool = False
    message: str = ""
    recipes: list[Recipe] = Field(default_factory=list)


class ForecastResult(BaseModel):
    """Burn-rate forecast result for a single item."""

    status: str
    item_id: str = ""
    item_name: str = ""
    current_stock: float = 0.0
    daily_burn_rate: float = 0.0
    weekend_multiplier: float = 1.0
    days_of_supply: Optional[float] = None
    predicted_runout_date: Optional[str] = None
    expiry_date: Optional[str] = None
    days_till_expiry: Optional[int] = None
    stock_status: str = ""  # Understocked | Well Stocked | Overstocked
    r_squared: float = 0.0
    data_points_used: int = 0
    message: str = ""


class HealthResponse(BaseModel):
    """System health check response."""

    status: str = "healthy"
    database: str = "connected"
    ai_api: str = "configured"
    grafana: str = "available"
    dev_mode: bool = False
    simulated_date: Optional[str] = None
    version: str = "3.1"
