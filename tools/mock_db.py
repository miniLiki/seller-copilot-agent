from __future__ import annotations

from itertools import count
from typing import Any

from .schemas import CreateTaskRequest, GenerateCopyRequest, InventoryStatus, ProductInfo


PRODUCTS: dict[str, dict[str, Any]] = {
    "SKU_001": {
        "product_id": "SKU_001",
        "title": "Portable Neck Fan",
        "market": "US",
        "category": "Summer Accessories",
        "price": 29.99,
        "inventory": 124,
        "hero_image_url": "data/images/sku_001_main.jpg",
        "status": "active",
    },
    "SKU_002": {
        "product_id": "SKU_002",
        "title": "Adjustable Laptop Stand",
        "market": "US",
        "category": "Office Accessories",
        "price": 39.99,
        "inventory": 46,
        "hero_image_url": "data/images/sku_002_main.jpg",
        "status": "active",
    },
}

INVENTORY: dict[str, dict[str, Any]] = {
    "SKU_001": {
        "product_id": "SKU_001",
        "inventory": 124,
        "safety_stock": 60,
        "risk_level": "low",
    },
    "SKU_002": {
        "product_id": "SKU_002",
        "inventory": 46,
        "safety_stock": 40,
        "risk_level": "medium",
    },
}

_TASK_COUNTER = count(1)
_CREATED_TASKS: list[dict[str, Any]] = []

COPY_TEMPLATES: dict[str, list[str]] = {
    "benefit_driven": [
        "Stay cool through long commutes with a lightweight hands-free fan.",
        "Beat the heat with portable airflow designed for busy summer days.",
        "Comfort-first cooling that keeps work, travel, and errands moving.",
        "Fresh airflow anywhere without bulky gear or complicated setup.",
        "Designed for all-day comfort when temperatures keep climbing.",
    ],
    "pain_point": [
        "Still sweating on the train? Get personal cooling in seconds.",
        "When office AC is not enough, keep a quiet breeze within reach.",
        "Stop letting hot commutes ruin your day with instant wearable airflow.",
        "Heat and humidity should not slow you down on the go.",
        "Tired of sticky afternoons? Switch to portable cooling that travels well.",
    ],
    "discount": [
        "Summer-ready comfort at a price that makes upgrading easy.",
        "Refresh your daily routine with an easy-to-buy cooling essential.",
        "Grab practical cooling support before the hottest weeks arrive.",
        "Value-focused comfort made for travel, work, and weekends.",
        "An affordable way to stay cool wherever the day takes you.",
    ],
}


def get_product(product_id: str) -> ProductInfo | None:
    payload = PRODUCTS.get(product_id)
    return ProductInfo(**payload) if payload else None


def get_inventory(product_id: str) -> InventoryStatus | None:
    payload = INVENTORY.get(product_id)
    return InventoryStatus(**payload) if payload else None


def create_task(payload: CreateTaskRequest) -> dict[str, Any]:
    task_id = f"TASK_{next(_TASK_COUNTER):03d}"
    task = {
        "task_id": task_id,
        "product_id": payload.product_id,
        "task_type": payload.task_type,
        "priority": payload.priority,
        "status": "created",
        "reason": payload.reason,
    }
    _CREATED_TASKS.append(task)
    return task


def generate_copy(payload: GenerateCopyRequest) -> dict[str, Any]:
    templates = COPY_TEMPLATES[payload.angle]
    copies = []
    for index in range(payload.num_variants):
        base_line = templates[index % len(templates)]
        copies.append(f"[{payload.market}] {base_line} (Product: {payload.product_id})")
    return {"product_id": payload.product_id, "copies": copies}


def list_created_tasks() -> list[dict[str, Any]]:
    return list(_CREATED_TASKS)

