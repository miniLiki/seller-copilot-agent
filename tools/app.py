from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .store_factory import store
from .schemas import (
    ApprovalDecision,
    ApprovalRead,
    AuditLogRead,
    ChannelAccountCreate,
    ChannelAccountRead,
    ChannelListingCreate,
    ChannelListingRead,
    CreateTaskRequest,
    CreateTaskResponse,
    GenerateCopyRequest,
    GenerateCopyResponse,
    InventoryAdjustmentCommand,
    InventoryAdjustmentRead,
    InventoryBalanceRead,
    InventoryCommand,
    InventoryMovementRead,
    InventoryPolicyCreate,
    InventoryPolicyRead,
    InventoryStatus,
    ProductInfo,
    ProductTemplateCreate,
    ProductTemplateRead,
    ProductTemplateUpdate,
    PurchaseOrderCreate,
    PurchaseOrderRead,
    ReceiptCreate,
    ReceiptRead,
    SalesOrderCreate,
    SalesOrderRead,
    SkuCreate,
    SkuRead,
    SkuUpdate,
    StockTransferCreate,
    StockTransferRead,
    StockCountCreate,
    StockCountRead,
    SupplierCreate,
    SupplierRead,
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)

app = FastAPI(title="Seller Copilot Tools", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/product/{product_id}", response_model=ProductInfo)
def read_product(product_id: str) -> ProductInfo:
    product = store.legacy_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product not found: {product_id}")
    return product


@app.get("/inventory/{product_id}", response_model=InventoryStatus)
def read_inventory(product_id: str) -> InventoryStatus:
    inventory = store.legacy_inventory(product_id)
    if inventory is None:
        raise HTTPException(status_code=404, detail=f"Inventory not found: {product_id}")
    return inventory


@app.post("/task/create", response_model=CreateTaskResponse)
def create_optimization_task(payload: CreateTaskRequest) -> CreateTaskResponse:
    if store.legacy_product(payload.product_id) is None:
        raise HTTPException(status_code=404, detail=f"Product not found: {payload.product_id}")
    result = store.create_task(payload)
    return CreateTaskResponse(**result)


@app.post("/copy/generate", response_model=GenerateCopyResponse)
def generate_ad_copy(payload: GenerateCopyRequest) -> GenerateCopyResponse:
    if store.legacy_product(payload.product_id) is None:
        raise HTTPException(status_code=404, detail=f"Product not found: {payload.product_id}")
    result = store.generate_copy(payload)
    return GenerateCopyResponse(**result)


@app.get("/api/product-templates", response_model=list[ProductTemplateRead])
def list_product_templates() -> list[ProductTemplateRead]:
    return store.list_product_templates()


@app.post("/api/product-templates", response_model=ProductTemplateRead, status_code=status.HTTP_201_CREATED)
def create_product_template(payload: ProductTemplateCreate) -> ProductTemplateRead:
    return store.create_product_template(payload)


@app.patch("/api/product-templates/{template_id}", response_model=ProductTemplateRead)
def update_product_template(template_id: UUID, payload: ProductTemplateUpdate) -> ProductTemplateRead:
    return store.update_product_template(template_id, payload)


@app.delete("/api/product-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_template(template_id: UUID) -> None:
    store.delete_product_template(template_id)


@app.get("/api/skus", response_model=list[SkuRead])
def list_skus() -> list[SkuRead]:
    return store.list_skus()


@app.post("/api/skus", response_model=SkuRead, status_code=status.HTTP_201_CREATED)
def create_sku(payload: SkuCreate) -> SkuRead:
    return store.create_sku(payload)


@app.get("/api/skus/{sku_id}", response_model=SkuRead)
def get_sku(sku_id: UUID) -> SkuRead:
    return store.get_sku(sku_id)


@app.patch("/api/skus/{sku_id}", response_model=SkuRead)
def update_sku(sku_id: UUID, payload: SkuUpdate) -> SkuRead:
    return store.update_sku(sku_id, payload)


@app.delete("/api/skus/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sku(sku_id: UUID) -> None:
    store.delete_sku(sku_id)


@app.get("/api/warehouses", response_model=list[WarehouseRead])
def list_warehouses() -> list[WarehouseRead]:
    return store.list_warehouses()


@app.post("/api/warehouses", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
def create_warehouse(payload: WarehouseCreate) -> WarehouseRead:
    return store.create_warehouse(payload)


@app.patch("/api/warehouses/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(warehouse_id: UUID, payload: WarehouseUpdate) -> WarehouseRead:
    return store.update_warehouse(warehouse_id, payload)


@app.get("/api/suppliers", response_model=list[SupplierRead])
def list_suppliers() -> list[SupplierRead]:
    return store.list_suppliers()


@app.post("/api/suppliers", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate) -> SupplierRead:
    return store.create_supplier(payload)


@app.get("/api/channel-accounts", response_model=list[ChannelAccountRead])
def list_channel_accounts() -> list[ChannelAccountRead]:
    return store.list_channel_accounts()


@app.post("/api/channel-accounts", response_model=ChannelAccountRead, status_code=status.HTTP_201_CREATED)
def create_channel_account(payload: ChannelAccountCreate) -> ChannelAccountRead:
    return store.create_channel_account(payload)


@app.get("/api/channel-listings", response_model=list[ChannelListingRead])
def list_channel_listings() -> list[ChannelListingRead]:
    return store.list_channel_listings()


@app.post("/api/channel-listings", response_model=ChannelListingRead, status_code=status.HTTP_201_CREATED)
def create_channel_listing(payload: ChannelListingCreate) -> ChannelListingRead:
    return store.create_channel_listing(payload)


@app.get("/api/inventory-policies", response_model=list[InventoryPolicyRead])
def list_inventory_policies() -> list[InventoryPolicyRead]:
    return store.list_inventory_policies()


@app.post("/api/inventory-policies", response_model=InventoryPolicyRead, status_code=status.HTTP_201_CREATED)
def create_inventory_policy(payload: InventoryPolicyCreate) -> InventoryPolicyRead:
    return store.create_inventory_policy(payload)


@app.get("/api/inventory/balances", response_model=list[InventoryBalanceRead])
def list_inventory_balances() -> list[InventoryBalanceRead]:
    return store.list_inventory_balances()


@app.get("/api/inventory/movements", response_model=list[InventoryMovementRead])
def list_inventory_movements() -> list[InventoryMovementRead]:
    return store.list_movements()


@app.post("/api/inventory/receive", response_model=InventoryMovementRead)
def receive_inventory(payload: InventoryCommand) -> InventoryMovementRead:
    return store.inventory_command("receive", payload)


@app.post("/api/inventory/allocate", response_model=InventoryMovementRead)
def allocate_inventory(payload: InventoryCommand) -> InventoryMovementRead:
    return store.inventory_command("allocate", payload)


@app.post("/api/inventory/release", response_model=InventoryMovementRead)
def release_inventory(payload: InventoryCommand) -> InventoryMovementRead:
    return store.inventory_command("release", payload)


@app.post("/api/inventory/ship", response_model=InventoryMovementRead)
def ship_inventory(payload: InventoryCommand) -> InventoryMovementRead:
    return store.inventory_command("ship", payload)


@app.post("/api/inventory/damage", response_model=InventoryMovementRead)
def damage_inventory(payload: InventoryCommand) -> InventoryMovementRead:
    return store.inventory_command("damage", payload)


@app.post("/api/inventory/return", response_model=InventoryMovementRead)
def return_inventory(payload: InventoryCommand) -> InventoryMovementRead:
    return store.inventory_command("return", payload)


@app.post("/api/inventory/adjust", response_model=InventoryAdjustmentRead)
def adjust_inventory(payload: InventoryAdjustmentCommand) -> InventoryAdjustmentRead:
    return store.adjust_inventory(payload)


@app.get("/api/sales-orders", response_model=list[SalesOrderRead])
def list_sales_orders() -> list[SalesOrderRead]:
    return store.list_sales_orders()


@app.post("/api/sales-orders", response_model=SalesOrderRead, status_code=status.HTTP_201_CREATED)
def create_sales_order(payload: SalesOrderCreate) -> SalesOrderRead:
    return store.create_sales_order(payload)


@app.post("/api/sales-orders/{order_id}/cancel", response_model=SalesOrderRead)
def cancel_sales_order(order_id: UUID) -> SalesOrderRead:
    return store.cancel_sales_order(order_id)


@app.post("/api/sales-orders/{order_id}/ship", response_model=SalesOrderRead)
def ship_sales_order(order_id: UUID) -> SalesOrderRead:
    return store.ship_sales_order(order_id)


@app.get("/api/purchase-orders", response_model=list[PurchaseOrderRead])
def list_purchase_orders() -> list[PurchaseOrderRead]:
    return store.list_purchase_orders()


@app.post("/api/purchase-orders", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(payload: PurchaseOrderCreate) -> PurchaseOrderRead:
    return store.create_purchase_order(payload)


@app.post("/api/purchase-orders/{order_id}/submit", response_model=PurchaseOrderRead)
def submit_purchase_order(order_id: UUID) -> PurchaseOrderRead:
    return store.submit_purchase_order(order_id)


@app.post("/api/purchase-orders/{order_id}/cancel", response_model=PurchaseOrderRead)
def cancel_purchase_order(order_id: UUID) -> PurchaseOrderRead:
    return store.cancel_purchase_order(order_id)


@app.get("/api/receipts", response_model=list[ReceiptRead])
def list_receipts() -> list[ReceiptRead]:
    return store.list_receipts()


@app.post("/api/receipts", response_model=ReceiptRead, status_code=status.HTTP_201_CREATED)
def create_receipt(payload: ReceiptCreate) -> ReceiptRead:
    return store.create_receipt(payload)


@app.get("/api/stock-transfers", response_model=list[StockTransferRead])
def list_stock_transfers() -> list[StockTransferRead]:
    return store.list_stock_transfers()


@app.post("/api/stock-transfers", response_model=StockTransferRead, status_code=status.HTTP_201_CREATED)
def create_stock_transfer(payload: StockTransferCreate) -> StockTransferRead:
    return store.create_stock_transfer(payload)


@app.post("/api/stock-transfers/{transfer_id}/submit", response_model=StockTransferRead)
def submit_stock_transfer(transfer_id: UUID) -> StockTransferRead:
    return store.submit_stock_transfer(transfer_id)


@app.post("/api/stock-transfers/{transfer_id}/ship", response_model=StockTransferRead)
def ship_stock_transfer(transfer_id: UUID) -> StockTransferRead:
    return store.ship_stock_transfer(transfer_id)


@app.post("/api/stock-transfers/{transfer_id}/receive", response_model=StockTransferRead)
def receive_stock_transfer(transfer_id: UUID) -> StockTransferRead:
    return store.receive_stock_transfer(transfer_id)


@app.post("/api/stock-transfers/{transfer_id}/cancel", response_model=StockTransferRead)
def cancel_stock_transfer(transfer_id: UUID) -> StockTransferRead:
    return store.cancel_stock_transfer(transfer_id)


@app.get("/api/inventory-adjustments", response_model=list[InventoryAdjustmentRead])
def list_inventory_adjustments() -> list[InventoryAdjustmentRead]:
    return store.list_adjustments()


@app.post("/api/inventory-adjustments", response_model=InventoryAdjustmentRead, status_code=status.HTTP_201_CREATED)
def create_inventory_adjustment(payload: InventoryAdjustmentCommand) -> InventoryAdjustmentRead:
    return store.adjust_inventory(payload)


@app.post("/api/inventory-adjustments/{adjustment_id}/submit", response_model=InventoryAdjustmentRead)
def submit_inventory_adjustment(adjustment_id: UUID) -> InventoryAdjustmentRead:
    return store.submit_adjustment(adjustment_id)


@app.post("/api/inventory-adjustments/{adjustment_id}/apply", response_model=InventoryAdjustmentRead)
def apply_inventory_adjustment(adjustment_id: UUID) -> InventoryAdjustmentRead:
    return store.apply_adjustment(adjustment_id)


@app.get("/api/stock-counts", response_model=list[StockCountRead])
def list_stock_counts() -> list[StockCountRead]:
    return store.list_stock_counts()


@app.post("/api/stock-counts", response_model=StockCountRead, status_code=status.HTTP_201_CREATED)
def create_stock_count(payload: StockCountCreate) -> StockCountRead:
    return store.create_stock_count(payload)


@app.post("/api/stock-counts/{count_id}/submit", response_model=StockCountRead)
def submit_stock_count(count_id: UUID) -> StockCountRead:
    return store.submit_stock_count(count_id)


@app.post("/api/stock-counts/{count_id}/apply", response_model=StockCountRead)
def apply_stock_count(count_id: UUID) -> StockCountRead:
    return store.apply_stock_count(count_id)


@app.get("/api/approvals", response_model=list[ApprovalRead])
def list_approvals() -> list[ApprovalRead]:
    return store.list_approvals()


@app.post("/api/approvals/{approval_id}/approve", response_model=ApprovalRead)
def approve(approval_id: UUID, payload: ApprovalDecision) -> ApprovalRead:
    return store.approve(approval_id, payload)


@app.post("/api/approvals/{approval_id}/reject", response_model=ApprovalRead)
def reject(approval_id: UUID, payload: ApprovalDecision) -> ApprovalRead:
    return store.reject(approval_id, payload)


@app.get("/api/sync/jobs")
def list_sync_jobs() -> list[dict]:
    return store.list_sync_jobs()


@app.post("/api/sync/jobs")
def create_sync_job() -> dict:
    return store.create_sync_job()


@app.get("/api/sync/errors")
def list_sync_errors() -> list[dict]:
    return []


@app.get("/api/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs() -> list[AuditLogRead]:
    return store.list_audit_logs()
