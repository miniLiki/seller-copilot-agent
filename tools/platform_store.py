from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException

from .schemas import (
    ApprovalDecision,
    ApprovalRead,
    AuditLogRead,
    ChannelAccountCreate,
    ChannelAccountRead,
    ChannelListingCreate,
    ChannelListingRead,
    CreateTaskRequest,
    GenerateCopyRequest,
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


HIGH_RISK_ADJUSTMENT_THRESHOLD = 50


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _record(**values: Any) -> dict[str, Any]:
    timestamp = now_utc()
    return {"id": uuid4(), "created_at": timestamp, "updated_at": timestamp, **values}


def _touch(record: dict[str, Any]) -> None:
    record["updated_at"] = now_utc()


def _as_model(model, record: dict[str, Any]):
    return model(**deepcopy(record))


def _business_error(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message, "details": details or {}}})


class PlatformStore:
    """In-memory implementation of the inventory platform domain.

    The service keeps the mock-first demo path fast and deterministic while
    exposing the same business boundaries planned for the PostgreSQL version.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self.reset()

    def reset(self) -> None:
        with RLock():
            self.product_templates: dict[UUID, dict[str, Any]] = {}
            self.skus: dict[UUID, dict[str, Any]] = {}
            self.warehouses: dict[UUID, dict[str, Any]] = {}
            self.suppliers: dict[UUID, dict[str, Any]] = {}
            self.channel_accounts: dict[UUID, dict[str, Any]] = {}
            self.channel_listings: dict[UUID, dict[str, Any]] = {}
            self.inventory_balances: dict[tuple[UUID, UUID], dict[str, Any]] = {}
            self.inventory_movements: dict[UUID, dict[str, Any]] = {}
            self.inventory_policies: dict[UUID, dict[str, Any]] = {}
            self.sales_orders: dict[UUID, dict[str, Any]] = {}
            self.purchase_orders: dict[UUID, dict[str, Any]] = {}
            self.receipts: dict[UUID, dict[str, Any]] = {}
            self.stock_transfers: dict[UUID, dict[str, Any]] = {}
            self.stock_counts: dict[UUID, dict[str, Any]] = {}
            self.inventory_adjustments: dict[UUID, dict[str, Any]] = {}
            self.approvals: dict[UUID, dict[str, Any]] = {}
            self.audit_logs: dict[UUID, dict[str, Any]] = {}
            self.outbox_events: dict[UUID, dict[str, Any]] = {}
            self.sync_jobs: dict[UUID, dict[str, Any]] = {}
            self.sync_errors: dict[UUID, dict[str, Any]] = {}
            self.idempotency_results: dict[str, Any] = {}
            self.created_tasks: list[dict[str, Any]] = []
            self._seed()

    def _seed(self) -> None:
        template_1 = self.create_product_template(
            ProductTemplateCreate(
                product_code="PT_NECK_FAN",
                title="Portable Neck Fan",
                brand="DemoBrand",
                category="Summer Accessories",
                description="Hands-free cooling product.",
                default_market="US",
            )
        )
        template_2 = self.create_product_template(
            ProductTemplateCreate(
                product_code="PT_LAPTOP_STAND",
                title="Adjustable Laptop Stand",
                brand="DemoBrand",
                category="Office Accessories",
                description="Ergonomic laptop stand.",
                default_market="US",
            )
        )
        sku_1 = self.create_sku(
            SkuCreate(
                sku_code="SKU_001",
                product_template_id=template_1.id,
                title="Portable Neck Fan",
                market="US",
                price=29.99,
                hero_image_url="data/images/sku_001_main.jpg",
            )
        )
        sku_2 = self.create_sku(
            SkuCreate(
                sku_code="SKU_002",
                product_template_id=template_2.id,
                title="Adjustable Laptop Stand",
                market="US",
                price=39.99,
                hero_image_url="data/images/sku_002_main.jpg",
            )
        )
        warehouse = self.create_warehouse(WarehouseCreate(warehouse_code="US_WEST", name="US West Demo Warehouse", country="US", region="WEST"))
        self.create_supplier(SupplierCreate(supplier_code="SUP_DEMO", name="Demo Supplier", contact_email="ops@example.com"))
        account = self.create_channel_account(ChannelAccountCreate(channel="amazon", account_name="Demo Amazon US", market="US"))
        self.create_channel_listing(
            ChannelListingCreate(
                sku_id=sku_1.id,
                channel_account_id=account.id,
                external_listing_id="AMZ-SKU-001",
                external_sku="SKU_001",
                title=sku_1.title,
                price=sku_1.price,
            )
        )
        self.create_inventory_policy(
            InventoryPolicyCreate(sku_id=sku_1.id, warehouse_id=warehouse.id, reorder_point=60, reorder_qty=120, lead_time_days=14, service_level=0.95)
        )
        self.create_inventory_policy(
            InventoryPolicyCreate(sku_id=sku_2.id, warehouse_id=warehouse.id, reorder_point=40, reorder_qty=80, lead_time_days=14, service_level=0.95)
        )
        self._ensure_balance(sku_1.id, warehouse.id)
        self._ensure_balance(sku_2.id, warehouse.id)
        self._apply_inventory_delta(
            sku_id=sku_1.id,
            warehouse_id=warehouse.id,
            movement_type="receive",
            quantity=124,
            on_hand_delta=124,
            allocated_delta=0,
            damaged_delta=0,
            quarantine_delta=0,
            source_type="seed",
            source_id=None,
            reason="seed inventory",
            idempotency_key="seed-sku-001",
        )
        self._apply_inventory_delta(
            sku_id=sku_2.id,
            warehouse_id=warehouse.id,
            movement_type="receive",
            quantity=46,
            on_hand_delta=46,
            allocated_delta=0,
            damaged_delta=0,
            quarantine_delta=0,
            source_type="seed",
            source_id=None,
            reason="seed inventory",
            idempotency_key="seed-sku-002",
        )
        self.create_supplier(SupplierCreate(supplier_code="SUP_BACKUP", name="Backup Supplier", contact_email="backup@example.com"))

    def _unique(self, records: dict[UUID, dict[str, Any]], field: str, value: Any, *, exclude_id: UUID | None = None) -> None:
        for record_id, record in records.items():
            if record_id != exclude_id and record.get(field) == value:
                raise _business_error(409, "DUPLICATE_VALUE", f"{field} already exists.", {field: value})

    def _audit(self, action: str, entity_type: str, entity_id: UUID | None, after: Any = None, idempotency_key: str | None = None) -> None:
        item = _record(
            actor_user_id=None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=None,
            after_json=deepcopy(after) if isinstance(after, dict) else None,
            request_id=None,
            idempotency_key=idempotency_key,
        )
        self.audit_logs[item["id"]] = item

    def _outbox(self, event_type: str, aggregate_type: str, aggregate_id: UUID, payload: dict[str, Any]) -> None:
        item = _record(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=deepcopy(payload),
            status="pending",
            attempts=0,
            last_error=None,
            processed_at=None,
        )
        self.outbox_events[item["id"]] = item

    def create_product_template(self, payload: ProductTemplateCreate) -> ProductTemplateRead:
        with self._lock:
            self._unique(self.product_templates, "product_code", payload.product_code)
            item = _record(**payload.model_dump())
            self.product_templates[item["id"]] = item
            self._audit("create", "product_template", item["id"], item)
            return _as_model(ProductTemplateRead, item)

    def list_product_templates(self) -> list[ProductTemplateRead]:
        return [_as_model(ProductTemplateRead, item) for item in self.product_templates.values()]

    def update_product_template(self, template_id: UUID, payload: ProductTemplateUpdate) -> ProductTemplateRead:
        with self._lock:
            item = self.product_templates.get(template_id)
            if item is None:
                raise _business_error(404, "PRODUCT_TEMPLATE_NOT_FOUND", "Product template not found.")
            for key, value in payload.model_dump(exclude_unset=True).items():
                item[key] = value
            _touch(item)
            self._audit("update", "product_template", template_id, item)
            return _as_model(ProductTemplateRead, item)

    def delete_product_template(self, template_id: UUID) -> None:
        with self._lock:
            if any(sku["product_template_id"] == template_id for sku in self.skus.values()):
                raise _business_error(409, "PRODUCT_TEMPLATE_IN_USE", "Product template has SKUs.")
            if self.product_templates.pop(template_id, None) is None:
                raise _business_error(404, "PRODUCT_TEMPLATE_NOT_FOUND", "Product template not found.")
            self._audit("delete", "product_template", template_id)

    def create_sku(self, payload: SkuCreate) -> SkuRead:
        with self._lock:
            if payload.product_template_id not in self.product_templates:
                raise _business_error(404, "PRODUCT_TEMPLATE_NOT_FOUND", "Product template not found.")
            self._unique(self.skus, "sku_code", payload.sku_code)
            item = _record(**payload.model_dump())
            self.skus[item["id"]] = item
            self._audit("create", "sku", item["id"], item)
            return _as_model(SkuRead, item)

    def list_skus(self) -> list[SkuRead]:
        return [_as_model(SkuRead, item) for item in self.skus.values()]

    def get_sku(self, sku_id: UUID) -> SkuRead:
        item = self.skus.get(sku_id)
        if item is None:
            raise _business_error(404, "SKU_NOT_FOUND", "SKU not found.")
        return _as_model(SkuRead, item)

    def update_sku(self, sku_id: UUID, payload: SkuUpdate) -> SkuRead:
        with self._lock:
            item = self.skus.get(sku_id)
            if item is None:
                raise _business_error(404, "SKU_NOT_FOUND", "SKU not found.")
            for key, value in payload.model_dump(exclude_unset=True).items():
                item[key] = value
            _touch(item)
            self._audit("update", "sku", sku_id, item)
            return _as_model(SkuRead, item)

    def delete_sku(self, sku_id: UUID) -> None:
        with self._lock:
            if any(key[0] == sku_id for key in self.inventory_balances):
                raise _business_error(409, "SKU_HAS_INVENTORY", "SKU has inventory balances.")
            if self.skus.pop(sku_id, None) is None:
                raise _business_error(404, "SKU_NOT_FOUND", "SKU not found.")
            self._audit("delete", "sku", sku_id)

    def create_warehouse(self, payload: WarehouseCreate) -> WarehouseRead:
        with self._lock:
            self._unique(self.warehouses, "warehouse_code", payload.warehouse_code)
            item = _record(**payload.model_dump())
            self.warehouses[item["id"]] = item
            self._audit("create", "warehouse", item["id"], item)
            return _as_model(WarehouseRead, item)

    def list_warehouses(self) -> list[WarehouseRead]:
        return [_as_model(WarehouseRead, item) for item in self.warehouses.values()]

    def update_warehouse(self, warehouse_id: UUID, payload: WarehouseUpdate) -> WarehouseRead:
        with self._lock:
            item = self.warehouses.get(warehouse_id)
            if item is None:
                raise _business_error(404, "WAREHOUSE_NOT_FOUND", "Warehouse not found.")
            for key, value in payload.model_dump(exclude_unset=True).items():
                item[key] = value
            _touch(item)
            self._audit("update", "warehouse", warehouse_id, item)
            return _as_model(WarehouseRead, item)

    def create_supplier(self, payload: SupplierCreate) -> SupplierRead:
        with self._lock:
            self._unique(self.suppliers, "supplier_code", payload.supplier_code)
            item = _record(**payload.model_dump())
            self.suppliers[item["id"]] = item
            return _as_model(SupplierRead, item)

    def list_suppliers(self) -> list[SupplierRead]:
        return [_as_model(SupplierRead, item) for item in self.suppliers.values()]

    def create_channel_account(self, payload: ChannelAccountCreate) -> ChannelAccountRead:
        item = _record(**payload.model_dump())
        self.channel_accounts[item["id"]] = item
        return _as_model(ChannelAccountRead, item)

    def list_channel_accounts(self) -> list[ChannelAccountRead]:
        return [_as_model(ChannelAccountRead, item) for item in self.channel_accounts.values()]

    def create_channel_listing(self, payload: ChannelListingCreate) -> ChannelListingRead:
        with self._lock:
            if payload.sku_id not in self.skus:
                raise _business_error(404, "SKU_NOT_FOUND", "SKU not found.")
            if payload.channel_account_id not in self.channel_accounts:
                raise _business_error(404, "CHANNEL_ACCOUNT_NOT_FOUND", "Channel account not found.")
            for listing in self.channel_listings.values():
                if listing["channel_account_id"] == payload.channel_account_id and listing["external_listing_id"] == payload.external_listing_id:
                    raise _business_error(409, "DUPLICATE_CHANNEL_LISTING", "Channel listing already exists.")
            item = _record(last_synced_at=None, **payload.model_dump())
            self.channel_listings[item["id"]] = item
            self._outbox("channel_listing.changed", "channel_listing", item["id"], item)
            return _as_model(ChannelListingRead, item)

    def list_channel_listings(self) -> list[ChannelListingRead]:
        return [_as_model(ChannelListingRead, item) for item in self.channel_listings.values()]

    def create_inventory_policy(self, payload: InventoryPolicyCreate) -> InventoryPolicyRead:
        with self._lock:
            if payload.sku_id not in self.skus:
                raise _business_error(404, "SKU_NOT_FOUND", "SKU not found.")
            item = _record(**payload.model_dump())
            self.inventory_policies[item["id"]] = item
            return _as_model(InventoryPolicyRead, item)

    def list_inventory_policies(self) -> list[InventoryPolicyRead]:
        return [_as_model(InventoryPolicyRead, item) for item in self.inventory_policies.values()]

    def _ensure_balance(self, sku_id: UUID, warehouse_id: UUID) -> dict[str, Any]:
        if sku_id not in self.skus:
            raise _business_error(404, "SKU_NOT_FOUND", "SKU not found.")
        if warehouse_id not in self.warehouses:
            raise _business_error(404, "WAREHOUSE_NOT_FOUND", "Warehouse not found.")
        key = (sku_id, warehouse_id)
        if key not in self.inventory_balances:
            item = _record(
                sku_id=sku_id,
                warehouse_id=warehouse_id,
                on_hand=0,
                allocated=0,
                available_to_sell=0,
                inbound=0,
                damaged=0,
                quarantine=0,
                version=1,
            )
            self.inventory_balances[key] = item
        return self.inventory_balances[key]

    def _recalculate_balance(self, balance: dict[str, Any]) -> None:
        balance["available_to_sell"] = balance["on_hand"] - balance["allocated"] - balance["damaged"] - balance["quarantine"]
        balance["version"] += 1
        _touch(balance)

    def _policy_for(self, sku_id: UUID, warehouse_id: UUID | None) -> dict[str, Any] | None:
        fallback = None
        for policy in self.inventory_policies.values():
            if policy["sku_id"] == sku_id and policy["warehouse_id"] == warehouse_id:
                return policy
            if policy["sku_id"] == sku_id and policy["warehouse_id"] is None:
                fallback = policy
        return fallback

    def _risk_level(self, sku_id: UUID, warehouse_id: UUID, available_to_sell: int) -> str:
        policy = self._policy_for(sku_id, warehouse_id)
        if policy is None:
            return "low" if available_to_sell > 0 else "high"
        if available_to_sell <= policy["reorder_point"]:
            return "high"
        if available_to_sell <= policy["reorder_point"] + int(policy["reorder_qty"] * 0.25):
            return "medium"
        return "low"

    def _balance_read(self, balance: dict[str, Any]) -> InventoryBalanceRead:
        sku = self.skus[balance["sku_id"]]
        warehouse = self.warehouses[balance["warehouse_id"]]
        payload = dict(balance)
        payload["sku_code"] = sku["sku_code"]
        payload["warehouse_code"] = warehouse["warehouse_code"]
        payload["risk_level"] = self._risk_level(balance["sku_id"], balance["warehouse_id"], balance["available_to_sell"])
        return InventoryBalanceRead(**deepcopy(payload))

    def list_inventory_balances(self) -> list[InventoryBalanceRead]:
        return [self._balance_read(item) for item in self.inventory_balances.values()]

    def _apply_inventory_delta(
        self,
        *,
        sku_id: UUID,
        warehouse_id: UUID,
        movement_type: str,
        quantity: int,
        on_hand_delta: int,
        allocated_delta: int,
        damaged_delta: int,
        quarantine_delta: int,
        source_type: str,
        source_id: UUID | None,
        reason: str,
        idempotency_key: str | None,
    ) -> InventoryMovementRead:
        if idempotency_key and idempotency_key in self.idempotency_results:
            return self.idempotency_results[idempotency_key]
        balance = self._ensure_balance(sku_id, warehouse_id)
        next_on_hand = balance["on_hand"] + on_hand_delta
        next_allocated = balance["allocated"] + allocated_delta
        next_damaged = balance["damaged"] + damaged_delta
        next_quarantine = balance["quarantine"] + quarantine_delta
        next_available = next_on_hand - next_allocated - next_damaged - next_quarantine
        if min(next_on_hand, next_allocated, next_damaged, next_quarantine, next_available) < 0:
            raise _business_error(400, "INSUFFICIENT_AVAILABLE_STOCK", "Available stock is lower than requested quantity.")
        balance["on_hand"] = next_on_hand
        balance["allocated"] = next_allocated
        balance["damaged"] = next_damaged
        balance["quarantine"] = next_quarantine
        self._recalculate_balance(balance)
        movement = _record(
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            quantity=quantity,
            quantity_on_hand_delta=on_hand_delta,
            quantity_allocated_delta=allocated_delta,
            quantity_damaged_delta=damaged_delta,
            quantity_quarantine_delta=quarantine_delta,
            source_type=source_type,
            source_id=source_id,
            idempotency_key=idempotency_key,
            reason=reason,
            created_by=None,
        )
        self.inventory_movements[movement["id"]] = movement
        self._audit("inventory.command", "inventory_movement", movement["id"], movement, idempotency_key)
        self._outbox("inventory.changed", "sku", sku_id, {"sku_id": str(sku_id), "warehouse_id": str(warehouse_id), "movement_type": movement_type})
        result = _as_model(InventoryMovementRead, movement)
        if idempotency_key:
            self.idempotency_results[idempotency_key] = result
        return result

    def inventory_command(self, movement_type: str, payload: InventoryCommand) -> InventoryMovementRead:
        deltas = {
            "receive": (payload.quantity, 0, 0, 0),
            "allocate": (0, payload.quantity, 0, 0),
            "release": (0, -payload.quantity, 0, 0),
            "ship": (-payload.quantity, -payload.quantity, 0, 0),
            "damage": (0, 0, payload.quantity, 0),
            "return": (payload.quantity, 0, 0, 0),
        }
        if movement_type not in deltas:
            raise _business_error(400, "UNSUPPORTED_MOVEMENT_TYPE", "Unsupported movement type.")
        on_hand_delta, allocated_delta, damaged_delta, quarantine_delta = deltas[movement_type]
        with self._lock:
            return self._apply_inventory_delta(
                sku_id=payload.sku_id,
                warehouse_id=payload.warehouse_id,
                movement_type=movement_type,
                quantity=payload.quantity,
                on_hand_delta=on_hand_delta,
                allocated_delta=allocated_delta,
                damaged_delta=damaged_delta,
                quarantine_delta=quarantine_delta,
                source_type="inventory_command",
                source_id=None,
                reason=payload.reason,
                idempotency_key=payload.idempotency_key,
            )

    def adjust_inventory(self, payload: InventoryAdjustmentCommand) -> InventoryAdjustmentRead:
        with self._lock:
            if payload.idempotency_key in self.idempotency_results:
                return self.idempotency_results[payload.idempotency_key]
            adjustment = _record(
                adjustment_number=f"ADJ-{len(self.inventory_adjustments) + 1:04d}",
                sku_id=payload.sku_id,
                warehouse_id=payload.warehouse_id,
                quantity_delta=payload.quantity_delta,
                reason=payload.reason,
                status="pending" if abs(payload.quantity_delta) >= HIGH_RISK_ADJUSTMENT_THRESHOLD else "applied",
                approval_request_id=None,
                idempotency_key=payload.idempotency_key,
            )
            self.inventory_adjustments[adjustment["id"]] = adjustment
            if adjustment["status"] == "pending":
                approval = _record(
                    request_type="inventory_adjustment",
                    source_type="inventory_adjustment",
                    source_id=adjustment["id"],
                    status="pending",
                    requested_by=None,
                    approved_by=None,
                    requested_at=now_utc(),
                    decided_at=None,
                    reason=payload.reason,
                    decision_note=None,
                )
                self.approvals[approval["id"]] = approval
                adjustment["approval_request_id"] = approval["id"]
            else:
                self._apply_inventory_delta(
                    sku_id=payload.sku_id,
                    warehouse_id=payload.warehouse_id,
                    movement_type="adjust",
                    quantity=abs(payload.quantity_delta),
                    on_hand_delta=payload.quantity_delta,
                    allocated_delta=0,
                    damaged_delta=0,
                    quarantine_delta=0,
                    source_type="inventory_adjustment",
                    source_id=adjustment["id"],
                    reason=payload.reason,
                    idempotency_key=payload.idempotency_key,
                )
            result = _as_model(InventoryAdjustmentRead, adjustment)
            self.idempotency_results[payload.idempotency_key] = result
            return result

    def list_movements(self) -> list[InventoryMovementRead]:
        return [_as_model(InventoryMovementRead, item) for item in self.inventory_movements.values()]

    def create_sales_order(self, payload: SalesOrderCreate) -> SalesOrderRead:
        with self._lock:
            if payload.idempotency_key in self.idempotency_results:
                return self.idempotency_results[payload.idempotency_key]
            order = _record(
                order_number=payload.order_number,
                channel_account_id=payload.channel_account_id,
                status="reserved",
                customer_ref=payload.customer_ref,
                idempotency_key=payload.idempotency_key,
                lines=[],
            )
            for line in payload.lines:
                line_record = {"id": uuid4(), **line.model_dump(), "status": "reserved"}
                self._apply_inventory_delta(
                    sku_id=line.sku_id,
                    warehouse_id=line.warehouse_id,
                    movement_type="allocate",
                    quantity=line.quantity,
                    on_hand_delta=0,
                    allocated_delta=line.quantity,
                    damaged_delta=0,
                    quarantine_delta=0,
                    source_type="sales_order",
                    source_id=order["id"],
                    reason=f"reserve {payload.order_number}",
                    idempotency_key=f"{payload.idempotency_key}:allocate:{line.sku_id}:{line.warehouse_id}",
                )
                order["lines"].append(line_record)
            self.sales_orders[order["id"]] = order
            self.idempotency_results[payload.idempotency_key] = _as_model(SalesOrderRead, order)
            return self.idempotency_results[payload.idempotency_key]

    def list_sales_orders(self) -> list[SalesOrderRead]:
        return [_as_model(SalesOrderRead, item) for item in self.sales_orders.values()]

    def cancel_sales_order(self, order_id: UUID) -> SalesOrderRead:
        with self._lock:
            order = self.sales_orders.get(order_id)
            if order is None:
                raise _business_error(404, "SALES_ORDER_NOT_FOUND", "Sales order not found.")
            if order["status"] == "cancelled":
                return _as_model(SalesOrderRead, order)
            for line in order["lines"]:
                if line["status"] == "reserved":
                    self._apply_inventory_delta(
                        sku_id=line["sku_id"],
                        warehouse_id=line["warehouse_id"],
                        movement_type="release",
                        quantity=line["quantity"],
                        on_hand_delta=0,
                        allocated_delta=-line["quantity"],
                        damaged_delta=0,
                        quarantine_delta=0,
                        source_type="sales_order",
                        source_id=order_id,
                        reason=f"cancel {order['order_number']}",
                        idempotency_key=f"{order['idempotency_key']}:cancel:{line['id']}",
                    )
                    line["status"] = "cancelled"
            order["status"] = "cancelled"
            _touch(order)
            return _as_model(SalesOrderRead, order)

    def ship_sales_order(self, order_id: UUID) -> SalesOrderRead:
        with self._lock:
            order = self.sales_orders.get(order_id)
            if order is None:
                raise _business_error(404, "SALES_ORDER_NOT_FOUND", "Sales order not found.")
            for line in order["lines"]:
                if line["status"] == "reserved":
                    self._apply_inventory_delta(
                        sku_id=line["sku_id"],
                        warehouse_id=line["warehouse_id"],
                        movement_type="ship",
                        quantity=line["quantity"],
                        on_hand_delta=-line["quantity"],
                        allocated_delta=-line["quantity"],
                        damaged_delta=0,
                        quarantine_delta=0,
                        source_type="sales_order",
                        source_id=order_id,
                        reason=f"ship {order['order_number']}",
                        idempotency_key=f"{order['idempotency_key']}:ship:{line['id']}",
                    )
                    line["status"] = "shipped"
            order["status"] = "shipped"
            _touch(order)
            return _as_model(SalesOrderRead, order)

    def create_purchase_order(self, payload: PurchaseOrderCreate) -> PurchaseOrderRead:
        with self._lock:
            if payload.idempotency_key in self.idempotency_results:
                return self.idempotency_results[payload.idempotency_key]
            if payload.supplier_id not in self.suppliers:
                raise _business_error(404, "SUPPLIER_NOT_FOUND", "Supplier not found.")
            order = _record(
                po_number=payload.po_number,
                supplier_id=payload.supplier_id,
                warehouse_id=payload.warehouse_id,
                status="submitted",
                expected_arrival_at=payload.expected_arrival_at,
                idempotency_key=payload.idempotency_key,
                lines=[],
            )
            for line in payload.lines:
                self._ensure_balance(line.sku_id, payload.warehouse_id)["inbound"] += line.ordered_qty
                order["lines"].append({"id": uuid4(), **line.model_dump(), "received_qty": 0})
            self.purchase_orders[order["id"]] = order
            result = _as_model(PurchaseOrderRead, order)
            self.idempotency_results[payload.idempotency_key] = result
            return result

    def list_purchase_orders(self) -> list[PurchaseOrderRead]:
        return [_as_model(PurchaseOrderRead, item) for item in self.purchase_orders.values()]

    def submit_purchase_order(self, order_id: UUID) -> PurchaseOrderRead:
        order = self.purchase_orders.get(order_id)
        if order is None:
            raise _business_error(404, "PURCHASE_ORDER_NOT_FOUND", "Purchase order not found.")
        order["status"] = "submitted"
        _touch(order)
        return _as_model(PurchaseOrderRead, order)

    def cancel_purchase_order(self, order_id: UUID) -> PurchaseOrderRead:
        order = self.purchase_orders.get(order_id)
        if order is None:
            raise _business_error(404, "PURCHASE_ORDER_NOT_FOUND", "Purchase order not found.")
        if order["status"] != "cancelled":
            for line in order["lines"]:
                balance = self._ensure_balance(line["sku_id"], order["warehouse_id"])
                balance["inbound"] = max(0, balance["inbound"] - (line["ordered_qty"] - line["received_qty"]))
            order["status"] = "cancelled"
            _touch(order)
        return _as_model(PurchaseOrderRead, order)

    def create_receipt(self, payload: ReceiptCreate) -> ReceiptRead:
        with self._lock:
            if payload.idempotency_key in self.idempotency_results:
                return self.idempotency_results[payload.idempotency_key]
            receipt = _record(
                receipt_number=payload.receipt_number,
                purchase_order_id=payload.purchase_order_id,
                warehouse_id=payload.warehouse_id,
                status="received",
                received_at=now_utc(),
                idempotency_key=payload.idempotency_key,
                lines=[],
            )
            for line in payload.lines:
                damaged_delta = line.quantity if line.condition == "damaged" else 0
                quarantine_delta = line.quantity if line.condition == "quarantine" else 0
                movement_type = "damage" if line.condition == "damaged" else "receive"
                self._apply_inventory_delta(
                    sku_id=line.sku_id,
                    warehouse_id=payload.warehouse_id,
                    movement_type=movement_type,
                    quantity=line.quantity,
                    on_hand_delta=line.quantity,
                    allocated_delta=0,
                    damaged_delta=damaged_delta,
                    quarantine_delta=quarantine_delta,
                    source_type="receipt",
                    source_id=receipt["id"],
                    reason=f"receipt {payload.receipt_number}",
                    idempotency_key=f"{payload.idempotency_key}:receipt:{line.sku_id}",
                )
                balance = self._ensure_balance(line.sku_id, payload.warehouse_id)
                balance["inbound"] = max(0, balance["inbound"] - line.quantity)
                receipt["lines"].append({"id": uuid4(), **line.model_dump()})
            self.receipts[receipt["id"]] = receipt
            result = _as_model(ReceiptRead, receipt)
            self.idempotency_results[payload.idempotency_key] = result
            return result

    def list_receipts(self) -> list[ReceiptRead]:
        return [_as_model(ReceiptRead, item) for item in self.receipts.values()]

    def create_stock_transfer(self, payload: StockTransferCreate) -> StockTransferRead:
        with self._lock:
            transfer = _record(
                transfer_number=payload.transfer_number,
                from_warehouse_id=payload.from_warehouse_id,
                to_warehouse_id=payload.to_warehouse_id,
                status="submitted",
                idempotency_key=payload.idempotency_key,
                lines=[{"id": uuid4(), **line.model_dump(), "shipped_qty": 0, "received_qty": 0} for line in payload.lines],
            )
            for line in transfer["lines"]:
                self._apply_inventory_delta(
                    sku_id=line["sku_id"],
                    warehouse_id=payload.from_warehouse_id,
                    movement_type="allocate",
                    quantity=line["quantity"],
                    on_hand_delta=0,
                    allocated_delta=line["quantity"],
                    damaged_delta=0,
                    quarantine_delta=0,
                    source_type="stock_transfer",
                    source_id=transfer["id"],
                    reason=f"reserve transfer {payload.transfer_number}",
                    idempotency_key=f"{payload.idempotency_key}:submit:{line['sku_id']}",
                )
                self._ensure_balance(line["sku_id"], payload.to_warehouse_id)["inbound"] += line["quantity"]
            self.stock_transfers[transfer["id"]] = transfer
            return _as_model(StockTransferRead, transfer)

    def list_stock_transfers(self) -> list[StockTransferRead]:
        return [_as_model(StockTransferRead, item) for item in self.stock_transfers.values()]

    def submit_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        transfer = self.stock_transfers.get(transfer_id)
        if transfer is None:
            raise _business_error(404, "STOCK_TRANSFER_NOT_FOUND", "Stock transfer not found.")
        transfer["status"] = "submitted"
        _touch(transfer)
        return _as_model(StockTransferRead, transfer)

    def cancel_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        transfer = self.stock_transfers.get(transfer_id)
        if transfer is None:
            raise _business_error(404, "STOCK_TRANSFER_NOT_FOUND", "Stock transfer not found.")
        if transfer["status"] in {"received", "cancelled"}:
            return _as_model(StockTransferRead, transfer)
        for line in transfer["lines"]:
            if line["shipped_qty"] == 0:
                self._apply_inventory_delta(
                    sku_id=line["sku_id"],
                    warehouse_id=transfer["from_warehouse_id"],
                    movement_type="release",
                    quantity=line["quantity"],
                    on_hand_delta=0,
                    allocated_delta=-line["quantity"],
                    damaged_delta=0,
                    quarantine_delta=0,
                    source_type="stock_transfer",
                    source_id=transfer_id,
                    reason=f"cancel transfer {transfer['transfer_number']}",
                    idempotency_key=f"{transfer['idempotency_key']}:cancel:{line['sku_id']}",
                )
                inbound = self._ensure_balance(line["sku_id"], transfer["to_warehouse_id"])
                inbound["inbound"] = max(0, inbound["inbound"] - line["quantity"])
        transfer["status"] = "cancelled"
        _touch(transfer)
        return _as_model(StockTransferRead, transfer)

    def ship_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        transfer = self.stock_transfers.get(transfer_id)
        if transfer is None:
            raise _business_error(404, "STOCK_TRANSFER_NOT_FOUND", "Stock transfer not found.")
        for line in transfer["lines"]:
            if line["shipped_qty"] == 0:
                self._apply_inventory_delta(
                    sku_id=line["sku_id"],
                    warehouse_id=transfer["from_warehouse_id"],
                    movement_type="transfer_out",
                    quantity=line["quantity"],
                    on_hand_delta=-line["quantity"],
                    allocated_delta=-line["quantity"],
                    damaged_delta=0,
                    quarantine_delta=0,
                    source_type="stock_transfer",
                    source_id=transfer_id,
                    reason=f"ship transfer {transfer['transfer_number']}",
                    idempotency_key=f"{transfer['idempotency_key']}:ship:{line['sku_id']}",
                )
                line["shipped_qty"] = line["quantity"]
        transfer["status"] = "in_transit"
        _touch(transfer)
        return _as_model(StockTransferRead, transfer)

    def receive_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        transfer = self.stock_transfers.get(transfer_id)
        if transfer is None:
            raise _business_error(404, "STOCK_TRANSFER_NOT_FOUND", "Stock transfer not found.")
        for line in transfer["lines"]:
            if line["received_qty"] == 0:
                self._apply_inventory_delta(
                    sku_id=line["sku_id"],
                    warehouse_id=transfer["to_warehouse_id"],
                    movement_type="transfer_in",
                    quantity=line["quantity"],
                    on_hand_delta=line["quantity"],
                    allocated_delta=0,
                    damaged_delta=0,
                    quarantine_delta=0,
                    source_type="stock_transfer",
                    source_id=transfer_id,
                    reason=f"receive transfer {transfer['transfer_number']}",
                    idempotency_key=f"{transfer['idempotency_key']}:receive:{line['sku_id']}",
                )
                balance = self._ensure_balance(line["sku_id"], transfer["to_warehouse_id"])
                balance["inbound"] = max(0, balance["inbound"] - line["quantity"])
                line["received_qty"] = line["quantity"]
        transfer["status"] = "received"
        _touch(transfer)
        return _as_model(StockTransferRead, transfer)

    def list_adjustments(self) -> list[InventoryAdjustmentRead]:
        return [_as_model(InventoryAdjustmentRead, item) for item in self.inventory_adjustments.values()]

    def submit_adjustment(self, adjustment_id: UUID) -> InventoryAdjustmentRead:
        adjustment = self.inventory_adjustments.get(adjustment_id)
        if adjustment is None:
            raise _business_error(404, "INVENTORY_ADJUSTMENT_NOT_FOUND", "Inventory adjustment not found.")
        return _as_model(InventoryAdjustmentRead, adjustment)

    def apply_adjustment(self, adjustment_id: UUID) -> InventoryAdjustmentRead:
        adjustment = self.inventory_adjustments.get(adjustment_id)
        if adjustment is None:
            raise _business_error(404, "INVENTORY_ADJUSTMENT_NOT_FOUND", "Inventory adjustment not found.")
        if adjustment["status"] == "pending":
            raise _business_error(400, "APPROVAL_REQUIRED", "Pending adjustment requires approval before apply.")
        return _as_model(InventoryAdjustmentRead, adjustment)

    def create_stock_count(self, payload: StockCountCreate) -> StockCountRead:
        count = _record(
            count_number=payload.count_number,
            warehouse_id=payload.warehouse_id,
            status="draft",
            started_at=now_utc(),
            completed_at=None,
            lines=[
                {
                    "id": uuid4(),
                    "sku_id": line.sku_id,
                    "expected_qty": line.expected_qty,
                    "counted_qty": line.counted_qty,
                    "variance_qty": line.counted_qty - line.expected_qty,
                    "status": "open",
                }
                for line in payload.lines
            ],
        )
        self.stock_counts[count["id"]] = count
        return _as_model(StockCountRead, count)

    def list_stock_counts(self) -> list[StockCountRead]:
        return [_as_model(StockCountRead, item) for item in self.stock_counts.values()]

    def submit_stock_count(self, count_id: UUID) -> StockCountRead:
        count = self.stock_counts.get(count_id)
        if count is None:
            raise _business_error(404, "STOCK_COUNT_NOT_FOUND", "Stock count not found.")
        count["status"] = "submitted"
        count["completed_at"] = now_utc()
        _touch(count)
        return _as_model(StockCountRead, count)

    def apply_stock_count(self, count_id: UUID) -> StockCountRead:
        count = self.stock_counts.get(count_id)
        if count is None:
            raise _business_error(404, "STOCK_COUNT_NOT_FOUND", "Stock count not found.")
        for line in count["lines"]:
            if line["variance_qty"] != 0 and line["status"] != "applied":
                self._apply_inventory_delta(
                    sku_id=line["sku_id"],
                    warehouse_id=count["warehouse_id"],
                    movement_type="adjust",
                    quantity=abs(line["variance_qty"]),
                    on_hand_delta=line["variance_qty"],
                    allocated_delta=0,
                    damaged_delta=0,
                    quarantine_delta=0,
                    source_type="stock_count",
                    source_id=count_id,
                    reason=f"stock count {count['count_number']}",
                    idempotency_key=f"stock-count:{count_id}:{line['sku_id']}",
                )
                line["status"] = "applied"
        count["status"] = "applied"
        _touch(count)
        return _as_model(StockCountRead, count)

    def list_approvals(self) -> list[ApprovalRead]:
        return [_as_model(ApprovalRead, item) for item in self.approvals.values()]

    def approve(self, approval_id: UUID, payload: ApprovalDecision) -> ApprovalRead:
        with self._lock:
            approval = self.approvals.get(approval_id)
            if approval is None:
                raise _business_error(404, "APPROVAL_NOT_FOUND", "Approval not found.")
            adjustment = self.inventory_adjustments[approval["source_id"]]
            self._apply_inventory_delta(
                sku_id=adjustment["sku_id"],
                warehouse_id=adjustment["warehouse_id"],
                movement_type="adjust",
                quantity=abs(adjustment["quantity_delta"]),
                on_hand_delta=adjustment["quantity_delta"],
                allocated_delta=0,
                damaged_delta=0,
                quarantine_delta=0,
                source_type="inventory_adjustment",
                source_id=adjustment["id"],
                reason=adjustment["reason"],
                idempotency_key=f"{adjustment['idempotency_key']}:approved",
            )
            approval["status"] = "approved"
            approval["decision_note"] = payload.decision_note
            approval["decided_at"] = now_utc()
            adjustment["status"] = "applied"
            _touch(adjustment)
            return _as_model(ApprovalRead, approval)

    def reject(self, approval_id: UUID, payload: ApprovalDecision) -> ApprovalRead:
        approval = self.approvals.get(approval_id)
        if approval is None:
            raise _business_error(404, "APPROVAL_NOT_FOUND", "Approval not found.")
        approval["status"] = "rejected"
        approval["decision_note"] = payload.decision_note
        approval["decided_at"] = now_utc()
        self.inventory_adjustments[approval["source_id"]]["status"] = "rejected"
        return _as_model(ApprovalRead, approval)

    def list_sync_jobs(self) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self.sync_jobs.values()]

    def create_sync_job(self) -> dict[str, Any]:
        account_id = next(iter(self.channel_accounts.keys()), None)
        job = _record(channel_account_id=account_id, status="succeeded", started_at=now_utc(), finished_at=now_utc(), summary={"pending_events": len(self.outbox_events)})
        self.sync_jobs[job["id"]] = job
        for event in self.outbox_events.values():
            event["status"] = "sent"
            event["processed_at"] = now_utc()
        return deepcopy(job)

    def list_audit_logs(self) -> list[AuditLogRead]:
        return [_as_model(AuditLogRead, item) for item in self.audit_logs.values()]

    def legacy_product(self, product_id: str) -> ProductInfo | None:
        sku = next((item for item in self.skus.values() if item["sku_code"] == product_id), None)
        if sku is None:
            return None
        template = self.product_templates[sku["product_template_id"]]
        inventory = sum(balance["available_to_sell"] for balance in self.inventory_balances.values() if balance["sku_id"] == sku["id"])
        return ProductInfo(
            product_id=sku["sku_code"],
            title=sku["title"],
            market=sku["market"],
            category=template["category"],
            price=sku["price"],
            inventory=inventory,
            hero_image_url=sku["hero_image_url"],
            status=sku["status"],
        )

    def legacy_inventory(self, product_id: str) -> InventoryStatus | None:
        sku = next((item for item in self.skus.values() if item["sku_code"] == product_id), None)
        if sku is None:
            return None
        balances = [balance for balance in self.inventory_balances.values() if balance["sku_id"] == sku["id"]]
        inventory = sum(balance["available_to_sell"] for balance in balances)
        policy = self._policy_for(sku["id"], balances[0]["warehouse_id"] if balances else None)
        safety_stock = policy["reorder_point"] if policy else 0
        risk = "low"
        for balance in balances:
            risk = max([risk, self._risk_level(sku["id"], balance["warehouse_id"], balance["available_to_sell"])], key={"low": 0, "medium": 1, "high": 2}.get)
        return InventoryStatus(product_id=sku["sku_code"], inventory=inventory, safety_stock=safety_stock, risk_level=risk)

    def create_task(self, payload: CreateTaskRequest) -> dict[str, Any]:
        task = {
            "task_id": f"TASK_{len(self.created_tasks) + 1:03d}",
            "product_id": payload.product_id,
            "task_type": payload.task_type,
            "priority": payload.priority,
            "status": "created",
            "reason": payload.reason,
        }
        self.created_tasks.append(task)
        return task

    def generate_copy(self, payload: GenerateCopyRequest) -> dict[str, Any]:
        templates = {
            "benefit_driven": [
                "Stay cool through long commutes with a lightweight hands-free fan.",
                "Beat the heat with portable airflow designed for busy summer days.",
                "Comfort-first cooling that keeps work, travel, and errands moving.",
            ],
            "pain_point": [
                "Still sweating on the train? Get personal cooling in seconds.",
                "When office AC is not enough, keep a quiet breeze within reach.",
                "Stop letting hot commutes ruin your day with instant wearable airflow.",
            ],
            "discount": [
                "Summer-ready comfort at a price that makes upgrading easy.",
                "Refresh your daily routine with an easy-to-buy cooling essential.",
                "Grab practical cooling support before the hottest weeks arrive.",
            ],
        }
        copies = [f"[{payload.market}] {templates[payload.angle][index % len(templates[payload.angle])]} (Product: {payload.product_id})" for index in range(payload.num_variants)]
        return {"product_id": payload.product_id, "copies": copies}


store = PlatformStore()
