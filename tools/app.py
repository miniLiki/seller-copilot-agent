from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .mock_db import create_task, generate_copy, get_inventory, get_product
from .schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    GenerateCopyRequest,
    GenerateCopyResponse,
    InventoryStatus,
    ProductInfo,
)

app = FastAPI(title="Seller Copilot Tools", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/product/{product_id}", response_model=ProductInfo)
def read_product(product_id: str) -> ProductInfo:
    product = get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product not found: {product_id}")
    return product


@app.get("/inventory/{product_id}", response_model=InventoryStatus)
def read_inventory(product_id: str) -> InventoryStatus:
    inventory = get_inventory(product_id)
    if inventory is None:
        raise HTTPException(status_code=404, detail=f"Inventory not found: {product_id}")
    return inventory


@app.post("/task/create", response_model=CreateTaskResponse)
def create_optimization_task(payload: CreateTaskRequest) -> CreateTaskResponse:
    if get_product(payload.product_id) is None:
        raise HTTPException(status_code=404, detail=f"Product not found: {payload.product_id}")
    result = create_task(payload)
    return CreateTaskResponse(**result)


@app.post("/copy/generate", response_model=GenerateCopyResponse)
def generate_ad_copy(payload: GenerateCopyRequest) -> GenerateCopyResponse:
    if get_product(payload.product_id) is None:
        raise HTTPException(status_code=404, detail=f"Product not found: {payload.product_id}")
    result = generate_copy(payload)
    return GenerateCopyResponse(**result)

