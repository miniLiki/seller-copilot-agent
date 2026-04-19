from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class TimestampMixin:
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    role_key: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)


class Permission(TimestampMixin, Base):
    __tablename__ = "permissions"
    permission_key: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class ProductTemplate(TimestampMixin, Base):
    __tablename__ = "product_templates"
    product_code: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    default_market: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)


class Sku(TimestampMixin, Base):
    __tablename__ = "skus"
    sku_code: Mapped[str] = mapped_column(Text, unique=True)
    product_template_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("product_templates.id"))
    title: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    hero_image_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)


class Warehouse(TimestampMixin, Base):
    __tablename__ = "warehouses"
    warehouse_code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"
    supplier_code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)


class ChannelAccount(TimestampMixin, Base):
    __tablename__ = "channel_accounts"
    channel: Mapped[str] = mapped_column(Text)
    account_name: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    credentials_ref: Mapped[str | None] = mapped_column(Text)


class ChannelListing(TimestampMixin, Base):
    __tablename__ = "channel_listings"
    __table_args__ = (UniqueConstraint("channel_account_id", "external_listing_id"),)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    channel_account_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("channel_accounts.id"))
    external_listing_id: Mapped[str] = mapped_column(Text)
    external_sku: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventoryBalance(TimestampMixin, Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (UniqueConstraint("sku_id", "warehouse_id"),)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    allocated: Mapped[int] = mapped_column(Integer, default=0)
    available_to_sell: Mapped[int] = mapped_column(Integer, default=0)
    inbound: Mapped[int] = mapped_column(Integer, default=0)
    damaged: Mapped[int] = mapped_column(Integer, default=0)
    quarantine: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    movement_type: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    quantity_on_hand_delta: Mapped[int] = mapped_column(Integer, default=0)
    quantity_allocated_delta: Mapped[int] = mapped_column(Integer, default=0)
    quantity_damaged_delta: Mapped[int] = mapped_column(Integer, default=0)
    quantity_quarantine_delta: Mapped[int] = mapped_column(Integer, default=0)
    source_type: Mapped[str] = mapped_column(Text)
    source_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryPolicy(TimestampMixin, Base):
    __tablename__ = "inventory_policies"
    __table_args__ = (UniqueConstraint("sku_id", "warehouse_id"),)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    reorder_point: Mapped[int] = mapped_column(Integer)
    reorder_qty: Mapped[int] = mapped_column(Integer)
    lead_time_days: Mapped[int] = mapped_column(Integer)
    service_level: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    coverage_days_target: Mapped[int | None] = mapped_column(Integer)


class SalesOrder(TimestampMixin, Base):
    __tablename__ = "sales_orders"
    order_number: Mapped[str] = mapped_column(Text, unique=True)
    channel_account_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("channel_accounts.id"))
    status: Mapped[str] = mapped_column(Text)
    customer_ref: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)


class SalesOrderLine(TimestampMixin, Base):
    __tablename__ = "sales_order_lines"
    sales_order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sales_orders.id"))
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)


class PurchaseOrder(TimestampMixin, Base):
    __tablename__ = "purchase_orders"
    po_number: Mapped[str] = mapped_column(Text, unique=True)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("suppliers.id"))
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(Text)
    expected_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)


class PurchaseOrderLine(TimestampMixin, Base):
    __tablename__ = "purchase_order_lines"
    purchase_order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    ordered_qty: Mapped[int] = mapped_column(Integer)
    received_qty: Mapped[int] = mapped_column(Integer, default=0)


class Receipt(TimestampMixin, Base):
    __tablename__ = "receipts"
    receipt_number: Mapped[str] = mapped_column(Text, unique=True)
    purchase_order_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)


class ReceiptLine(TimestampMixin, Base):
    __tablename__ = "receipt_lines"
    receipt_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("receipts.id"))
    purchase_order_line_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("purchase_order_lines.id"))
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    condition: Mapped[str] = mapped_column(Text)


class StockTransfer(TimestampMixin, Base):
    __tablename__ = "stock_transfers"
    transfer_number: Mapped[str] = mapped_column(Text, unique=True)
    from_warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    to_warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)


class StockTransferLine(TimestampMixin, Base):
    __tablename__ = "stock_transfer_lines"
    stock_transfer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("stock_transfers.id"))
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    shipped_qty: Mapped[int] = mapped_column(Integer, default=0)
    received_qty: Mapped[int] = mapped_column(Integer, default=0)


class InventoryAdjustment(TimestampMixin, Base):
    __tablename__ = "inventory_adjustments"
    adjustment_number: Mapped[str] = mapped_column(Text, unique=True)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    quantity_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    approval_request_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("approval_requests.id"))
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)


class StockCount(TimestampMixin, Base):
    __tablename__ = "stock_counts"
    count_number: Mapped[str] = mapped_column(Text, unique=True)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StockCountLine(TimestampMixin, Base):
    __tablename__ = "stock_count_lines"
    stock_count_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("stock_counts.id"))
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("skus.id"))
    expected_qty: Mapped[int] = mapped_column(Integer)
    counted_qty: Mapped[int] = mapped_column(Integer)
    variance_qty: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "approval_requests"
    request_type: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    source_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    decision_note: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    actor_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    before_json: Mapped[dict | None] = mapped_column(JSONB)
    after_json: Mapped[dict | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    event_type: Mapped[str] = mapped_column(Text)
    aggregate_type: Mapped[str] = mapped_column(Text)
    aggregate_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventorySyncJob(TimestampMixin, Base):
    __tablename__ = "inventory_sync_jobs"
    channel_account_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("channel_accounts.id"))
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[dict | None] = mapped_column(JSONB)


class SyncError(Base):
    __tablename__ = "sync_errors"
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    sync_job_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("inventory_sync_jobs.id"))
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    error_code: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
