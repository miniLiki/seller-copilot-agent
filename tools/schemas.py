from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high"]
TaskType = Literal["creative_refresh", "detail_page_fix", "title_rewrite"]
Priority = Literal["low", "medium", "high"]
CopyAngle = Literal["benefit_driven", "pain_point", "discount"]
RecordStatus = Literal["active", "draft", "archived", "inactive"]
WarehouseStatus = Literal["active", "inactive"]
MovementType = Literal["receive", "ship", "allocate", "release", "adjust", "damage", "transfer_out", "transfer_in", "return"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
OrderStatus = Literal["draft", "reserved", "cancelled", "shipped"]
PurchaseOrderStatus = Literal["draft", "submitted", "partially_received", "received", "cancelled"]
TransferStatus = Literal["draft", "submitted", "in_transit", "received", "cancelled"]


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


class ErrorEnvelope(BaseModel):
    error: dict[str, Any]


class ProductTemplateCreate(BaseModel):
    product_code: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2)
    brand: str | None = None
    category: str = Field(min_length=2)
    description: str | None = None
    default_market: str | None = None
    status: RecordStatus = "active"


class ProductTemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2)
    brand: str | None = None
    category: str | None = Field(default=None, min_length=2)
    description: str | None = None
    default_market: str | None = None
    status: RecordStatus | None = None


class ProductTemplateRead(ProductTemplateCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class SkuCreate(BaseModel):
    sku_code: str = Field(min_length=2, max_length=64)
    product_template_id: UUID
    title: str = Field(min_length=2)
    market: str = Field(min_length=2, max_length=8)
    price: float = Field(ge=0)
    hero_image_url: str = Field(min_length=1)
    status: RecordStatus = "active"


class SkuUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2)
    market: str | None = Field(default=None, min_length=2, max_length=8)
    price: float | None = Field(default=None, ge=0)
    hero_image_url: str | None = Field(default=None, min_length=1)
    status: RecordStatus | None = None


class SkuRead(SkuCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class WarehouseCreate(BaseModel):
    warehouse_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2)
    country: str | None = None
    region: str | None = None
    status: WarehouseStatus = "active"


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    country: str | None = None
    region: str | None = None
    status: WarehouseStatus | None = None


class WarehouseRead(WarehouseCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class SupplierCreate(BaseModel):
    supplier_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2)
    contact_email: str | None = None
    status: RecordStatus = "active"


class SupplierRead(SupplierCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ChannelAccountCreate(BaseModel):
    channel: str = Field(min_length=2)
    account_name: str = Field(min_length=2)
    market: str = Field(min_length=2, max_length=8)
    status: RecordStatus = "active"
    credentials_ref: str | None = None


class ChannelAccountRead(ChannelAccountCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ChannelListingCreate(BaseModel):
    sku_id: UUID
    channel_account_id: UUID
    external_listing_id: str = Field(min_length=1)
    external_sku: str | None = None
    title: str | None = None
    price: float | None = Field(default=None, ge=0)
    status: RecordStatus = "active"


class ChannelListingRead(ChannelListingCreate):
    id: UUID
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InventoryPolicyCreate(BaseModel):
    sku_id: UUID
    warehouse_id: UUID | None = None
    reorder_point: int = Field(ge=0)
    reorder_qty: int = Field(ge=0)
    lead_time_days: int = Field(ge=0)
    service_level: float = Field(ge=0, le=1)
    coverage_days_target: int | None = Field(default=None, ge=0)


class InventoryPolicyRead(InventoryPolicyCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class InventoryBalanceRead(BaseModel):
    id: UUID
    sku_id: UUID
    sku_code: str
    warehouse_id: UUID
    warehouse_code: str
    on_hand: int
    allocated: int
    available_to_sell: int
    inbound: int
    damaged: int
    quarantine: int
    risk_level: RiskLevel
    version: int
    created_at: datetime
    updated_at: datetime


class InventoryCommand(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=4)


class InventoryAdjustmentCommand(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    quantity_delta: int
    reason: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=4)


class InventoryMovementRead(BaseModel):
    id: UUID
    sku_id: UUID
    warehouse_id: UUID
    movement_type: MovementType
    quantity: int
    quantity_on_hand_delta: int
    quantity_allocated_delta: int
    quantity_damaged_delta: int
    quantity_quarantine_delta: int
    source_type: str
    source_id: UUID | None = None
    idempotency_key: str | None = None
    reason: str | None = None
    created_by: UUID | None = None
    created_at: datetime


class SalesOrderLineCreate(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    quantity: int = Field(gt=0)


class SalesOrderCreate(BaseModel):
    order_number: str = Field(min_length=2)
    channel_account_id: UUID | None = None
    customer_ref: str | None = None
    idempotency_key: str = Field(min_length=4)
    lines: list[SalesOrderLineCreate] = Field(min_length=1)


class SalesOrderRead(BaseModel):
    id: UUID
    order_number: str
    status: OrderStatus
    customer_ref: str | None = None
    idempotency_key: str | None = None
    lines: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class PurchaseOrderLineCreate(BaseModel):
    sku_id: UUID
    ordered_qty: int = Field(gt=0)


class PurchaseOrderCreate(BaseModel):
    po_number: str = Field(min_length=2)
    supplier_id: UUID
    warehouse_id: UUID
    expected_arrival_at: datetime | None = None
    idempotency_key: str = Field(min_length=4)
    lines: list[PurchaseOrderLineCreate] = Field(min_length=1)


class PurchaseOrderRead(BaseModel):
    id: UUID
    po_number: str
    supplier_id: UUID
    warehouse_id: UUID
    status: PurchaseOrderStatus
    lines: list[dict[str, Any]]
    idempotency_key: str | None = None
    created_at: datetime
    updated_at: datetime


class ReceiptLineCreate(BaseModel):
    purchase_order_line_id: UUID | None = None
    sku_id: UUID
    quantity: int = Field(gt=0)
    condition: Literal["sellable", "damaged", "quarantine"] = "sellable"


class ReceiptCreate(BaseModel):
    receipt_number: str = Field(min_length=2)
    purchase_order_id: UUID | None = None
    warehouse_id: UUID
    idempotency_key: str = Field(min_length=4)
    lines: list[ReceiptLineCreate] = Field(min_length=1)


class ReceiptRead(BaseModel):
    id: UUID
    receipt_number: str
    status: str
    received_at: datetime
    lines: list[dict[str, Any]]
    idempotency_key: str | None = None


class StockTransferLineCreate(BaseModel):
    sku_id: UUID
    quantity: int = Field(gt=0)


class StockTransferCreate(BaseModel):
    transfer_number: str = Field(min_length=2)
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    idempotency_key: str = Field(min_length=4)
    lines: list[StockTransferLineCreate] = Field(min_length=1)


class StockTransferRead(BaseModel):
    id: UUID
    transfer_number: str
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    status: TransferStatus
    lines: list[dict[str, Any]]
    idempotency_key: str | None = None
    created_at: datetime
    updated_at: datetime


class StockCountLineCreate(BaseModel):
    sku_id: UUID
    expected_qty: int = Field(ge=0)
    counted_qty: int = Field(ge=0)


class StockCountCreate(BaseModel):
    count_number: str = Field(min_length=2)
    warehouse_id: UUID
    lines: list[StockCountLineCreate] = Field(min_length=1)


class StockCountRead(BaseModel):
    id: UUID
    count_number: str
    warehouse_id: UUID
    status: str
    lines: list[dict[str, Any]]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InventoryAdjustmentRead(BaseModel):
    id: UUID
    adjustment_number: str
    sku_id: UUID
    warehouse_id: UUID
    quantity_delta: int
    reason: str
    status: str
    approval_request_id: UUID | None = None
    idempotency_key: str | None = None
    created_at: datetime
    updated_at: datetime


class ApprovalRead(BaseModel):
    id: UUID
    request_type: str
    source_type: str
    source_id: UUID
    status: ApprovalStatus
    reason: str | None = None
    decision_note: str | None = None
    requested_at: datetime
    decided_at: datetime | None = None


class ApprovalDecision(BaseModel):
    decision_note: str | None = None


class SyncJobRead(BaseModel):
    id: UUID
    channel_account_id: UUID | None = None
    status: str
    summary: dict[str, Any]
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AuditLogRead(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None = None
    before_json: dict[str, Any] | None = None
    after_json: dict[str, Any] | None = None
    request_id: str | None = None
    idempotency_key: str | None = None
    created_at: datetime
