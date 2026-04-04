from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high"]
TaskType = Literal["creative_refresh", "detail_page_fix", "title_rewrite"]
Priority = Literal["low", "medium", "high"]
CopyAngle = Literal["benefit_driven", "pain_point", "discount"]


class ProductInfo(BaseModel):
    """Product snapshot returned by the mock tool service."""

    product_id: str
    title: str
    market: str
    category: str
    price: float
    inventory: int
    hero_image_url: str
    status: str


class InventoryStatus(BaseModel):
    """Inventory and risk view for a product."""

    product_id: str
    inventory: int
    safety_stock: int
    risk_level: RiskLevel


class CreateTaskRequest(BaseModel):
    """Payload for creating a remediation task."""

    product_id: str
    task_type: TaskType
    priority: Priority
    reason: str = Field(min_length=3)


class CreateTaskResponse(BaseModel):
    """Response for a created remediation task."""

    task_id: str
    product_id: str
    task_type: TaskType
    priority: Priority
    status: str


class GenerateCopyRequest(BaseModel):
    """Payload for generating ad copy variants."""

    product_id: str
    market: str
    angle: CopyAngle
    num_variants: int = Field(ge=1, le=5)


class GenerateCopyResponse(BaseModel):
    """Response containing generated copy variants."""

    product_id: str
    copies: list[str]

