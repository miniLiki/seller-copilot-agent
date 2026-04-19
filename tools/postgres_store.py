from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

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
    StockCountCreate,
    StockCountRead,
    StockTransferCreate,
    StockTransferRead,
    SupplierCreate,
    SupplierRead,
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)


HIGH_RISK_ADJUSTMENT_THRESHOLD = 50


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def business_error(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message, "details": details or {}}})


def as_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    for key, value in list(item.items()):
        if isinstance(value, Decimal):
            item[key] = float(value)
    return item


class PostgresStore:
    def __init__(self, session_factory: sessionmaker[Session] | None) -> None:
        if session_factory is None:
            raise RuntimeError("PostgreSQL storage requires SQLAlchemy dependencies.")
        self.session_factory = session_factory

    def _read(self, fn: Callable[[Session], Any]) -> Any:
        with self.session_factory() as session:
            return fn(session)

    def _write(self, fn: Callable[[Session], Any]) -> Any:
        try:
            with self.session_factory.begin() as session:
                return fn(session)
        except IntegrityError as exc:
            raise business_error(409, "CONSTRAINT_VIOLATION", "Database constraint violation.", {"detail": str(exc.orig)}) from exc
        except OperationalError as exc:
            raise business_error(503, "DATABASE_UNAVAILABLE", "PostgreSQL is unavailable.", {"detail": str(exc.orig)}) from exc

    def _one(self, session: Session, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        row = session.execute(text(sql), params or {}).mappings().first()
        return as_dict(row) if row else None

    def _all(self, session: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [as_dict(row) for row in session.execute(text(sql), params or {}).mappings().all()]

    def _exec(self, session: Session, sql: str, params: dict[str, Any] | None = None) -> None:
        session.execute(text(sql), params or {})

    def _model(self, model: Any, row: dict[str, Any]) -> Any:
        return model(**row)

    def _audit(self, session: Session, action: str, entity_type: str, entity_id: UUID | None, after: dict[str, Any] | None = None, idempotency_key: str | None = None) -> None:
        self._exec(
            session,
            """
            INSERT INTO audit_logs (action, entity_type, entity_id, after_json, idempotency_key)
            VALUES (:action, :entity_type, :entity_id, CAST(:after_json AS jsonb), :idempotency_key)
            """,
            {
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "after_json": self._json(after),
                "idempotency_key": idempotency_key,
            },
        )

    def _outbox(self, session: Session, event_type: str, aggregate_type: str, aggregate_id: UUID, payload: dict[str, Any]) -> None:
        self._exec(
            session,
            """
            INSERT INTO outbox_events (event_type, aggregate_type, aggregate_id, payload, status, attempts)
            VALUES (:event_type, :aggregate_type, :aggregate_id, CAST(:payload AS jsonb), 'pending', 0)
            """,
            {"event_type": event_type, "aggregate_type": aggregate_type, "aggregate_id": aggregate_id, "payload": self._json(payload)},
        )

    def _json(self, payload: dict[str, Any] | None) -> str | None:
        if payload is None:
            return None
        import json

        return json.dumps(payload, default=str)

    def _risk_level(self, available_to_sell: int, policy: dict[str, Any] | None) -> str:
        if policy is None:
            return "low" if available_to_sell > 0 else "high"
        if available_to_sell <= policy["reorder_point"]:
            return "high"
        if available_to_sell <= policy["reorder_point"] + int(policy["reorder_qty"] * 0.25):
            return "medium"
        return "low"

    def _effective_policy(self, session: Session, sku_id: UUID, warehouse_id: UUID | None) -> dict[str, Any] | None:
        if warehouse_id is not None:
            policy = self._one(
                session,
                "SELECT * FROM inventory_policies WHERE sku_id = :sku_id AND warehouse_id = :warehouse_id LIMIT 1",
                {"sku_id": sku_id, "warehouse_id": warehouse_id},
            )
            if policy:
                return policy
        return self._one(session, "SELECT * FROM inventory_policies WHERE sku_id = :sku_id AND warehouse_id IS NULL LIMIT 1", {"sku_id": sku_id})

    def _balance(self, session: Session, sku_id: UUID, warehouse_id: UUID, *, lock: bool = False) -> dict[str, Any]:
        suffix = " FOR UPDATE" if lock else ""
        row = self._one(
            session,
            f"SELECT * FROM inventory_balances WHERE sku_id = :sku_id AND warehouse_id = :warehouse_id{suffix}",
            {"sku_id": sku_id, "warehouse_id": warehouse_id},
        )
        if row:
            return row
        if lock:
            inserted = self._one(
                session,
                """
                INSERT INTO inventory_balances (sku_id, warehouse_id, on_hand, allocated, available_to_sell, inbound, damaged, quarantine, version)
                VALUES (:sku_id, :warehouse_id, 0, 0, 0, 0, 0, 0, 1)
                RETURNING *
                """,
                {"sku_id": sku_id, "warehouse_id": warehouse_id},
            )
            if inserted:
                return inserted
        raise business_error(404, "INVENTORY_BALANCE_NOT_FOUND", "Inventory balance not found.")

    def _balance_read(self, session: Session, row: dict[str, Any]) -> InventoryBalanceRead:
        sku = self._one(session, "SELECT sku_code FROM skus WHERE id = :id", {"id": row["sku_id"]})
        warehouse = self._one(session, "SELECT warehouse_code FROM warehouses WHERE id = :id", {"id": row["warehouse_id"]})
        policy = self._effective_policy(session, row["sku_id"], row["warehouse_id"])
        payload = dict(row)
        payload["sku_code"] = sku["sku_code"] if sku else ""
        payload["warehouse_code"] = warehouse["warehouse_code"] if warehouse else ""
        payload["risk_level"] = self._risk_level(row["available_to_sell"], policy)
        return InventoryBalanceRead(**payload)

    def _update_balance(
        self,
        session: Session,
        balance: dict[str, Any],
        *,
        on_hand_delta: int,
        allocated_delta: int,
        damaged_delta: int,
        quarantine_delta: int,
    ) -> dict[str, Any]:
        next_on_hand = balance["on_hand"] + on_hand_delta
        next_allocated = balance["allocated"] + allocated_delta
        next_damaged = balance["damaged"] + damaged_delta
        next_quarantine = balance["quarantine"] + quarantine_delta
        next_available = next_on_hand - next_allocated - next_damaged - next_quarantine
        if min(next_on_hand, next_allocated, next_damaged, next_quarantine, next_available) < 0:
            raise business_error(400, "INSUFFICIENT_AVAILABLE_STOCK", "Available stock is lower than requested quantity.")
        return self._one(
            session,
            """
            UPDATE inventory_balances
            SET on_hand = :on_hand,
                allocated = :allocated,
                damaged = :damaged,
                quarantine = :quarantine,
                available_to_sell = :available_to_sell,
                version = version + 1,
                updated_at = now()
            WHERE id = :id
            RETURNING *
            """,
            {
                "id": balance["id"],
                "on_hand": next_on_hand,
                "allocated": next_allocated,
                "damaged": next_damaged,
                "quarantine": next_quarantine,
                "available_to_sell": next_available,
            },
        )

    def _apply_inventory_delta(
        self,
        session: Session,
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
        if idempotency_key:
            existing = self._one(session, "SELECT * FROM inventory_movements WHERE idempotency_key = :key", {"key": idempotency_key})
            if existing:
                return InventoryMovementRead(**existing)
        balance = self._balance(session, sku_id, warehouse_id, lock=True)
        self._update_balance(
            session,
            balance,
            on_hand_delta=on_hand_delta,
            allocated_delta=allocated_delta,
            damaged_delta=damaged_delta,
            quarantine_delta=quarantine_delta,
        )
        movement = self._one(
            session,
            """
            INSERT INTO inventory_movements (
              sku_id, warehouse_id, movement_type, quantity,
              quantity_on_hand_delta, quantity_allocated_delta, quantity_damaged_delta, quantity_quarantine_delta,
              source_type, source_id, idempotency_key, reason
            )
            VALUES (
              :sku_id, :warehouse_id, :movement_type, :quantity,
              :on_hand_delta, :allocated_delta, :damaged_delta, :quarantine_delta,
              :source_type, :source_id, :idempotency_key, :reason
            )
            RETURNING *
            """,
            {
                "sku_id": sku_id,
                "warehouse_id": warehouse_id,
                "movement_type": movement_type,
                "quantity": quantity,
                "on_hand_delta": on_hand_delta,
                "allocated_delta": allocated_delta,
                "damaged_delta": damaged_delta,
                "quarantine_delta": quarantine_delta,
                "source_type": source_type,
                "source_id": source_id,
                "idempotency_key": idempotency_key,
                "reason": reason,
            },
        )
        self._audit(session, "inventory.command", "inventory_movement", movement["id"], movement, idempotency_key)
        self._outbox(session, "inventory.changed", "sku", sku_id, {"sku_id": str(sku_id), "warehouse_id": str(warehouse_id), "movement_type": movement_type})
        return InventoryMovementRead(**movement)

    def legacy_product(self, product_id: str) -> ProductInfo | None:
        def run(session: Session) -> ProductInfo | None:
            row = self._one(
                session,
                """
                SELECT s.sku_code AS product_id, s.title, s.market, pt.category, s.price,
                       COALESCE(SUM(ib.available_to_sell), 0)::int AS inventory,
                       s.hero_image_url, s.status
                FROM skus s
                JOIN product_templates pt ON pt.id = s.product_template_id
                LEFT JOIN inventory_balances ib ON ib.sku_id = s.id
                WHERE s.sku_code = :sku_code
                GROUP BY s.id, pt.category
                """,
                {"sku_code": product_id},
            )
            return ProductInfo(**row) if row else None

        return self._read(run)

    def legacy_inventory(self, product_id: str) -> InventoryStatus | None:
        def run(session: Session) -> InventoryStatus | None:
            sku = self._one(session, "SELECT * FROM skus WHERE sku_code = :sku_code", {"sku_code": product_id})
            if not sku:
                return None
            balances = self._all(session, "SELECT * FROM inventory_balances WHERE sku_id = :sku_id", {"sku_id": sku["id"]})
            inventory = sum(row["available_to_sell"] for row in balances)
            policy = self._effective_policy(session, sku["id"], balances[0]["warehouse_id"] if balances else None)
            safety_stock = policy["reorder_point"] if policy else 0
            risk = "low"
            order = {"low": 0, "medium": 1, "high": 2}
            for balance in balances:
                risk = max(risk, self._risk_level(balance["available_to_sell"], self._effective_policy(session, sku["id"], balance["warehouse_id"])), key=order.get)
            return InventoryStatus(product_id=sku["sku_code"], inventory=inventory, safety_stock=safety_stock, risk_level=risk)

        return self._read(run)

    def create_task(self, payload: CreateTaskRequest) -> dict[str, Any]:
        def run(session: Session) -> dict[str, Any]:
            count = self._one(session, "SELECT count(*)::int AS count FROM audit_logs WHERE entity_type = 'optimization_task'")["count"]
            task = {
                "task_id": f"TASK_{count + 1:03d}",
                "product_id": payload.product_id,
                "task_type": payload.task_type,
                "priority": payload.priority,
                "status": "created",
                "reason": payload.reason,
            }
            self._audit(session, "create", "optimization_task", None, task)
            return task

        return self._write(run)

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

    def list_product_templates(self) -> list[ProductTemplateRead]:
        return self._read(lambda session: [ProductTemplateRead(**row) for row in self._all(session, "SELECT * FROM product_templates ORDER BY product_code")])

    def create_product_template(self, payload: ProductTemplateCreate) -> ProductTemplateRead:
        return self._write(lambda session: ProductTemplateRead(**self._one(session, "INSERT INTO product_templates (product_code, title, brand, category, description, default_market, status) VALUES (:product_code, :title, :brand, :category, :description, :default_market, :status) RETURNING *", payload.model_dump())))

    def update_product_template(self, template_id: UUID, payload: ProductTemplateUpdate) -> ProductTemplateRead:
        def run(session: Session) -> ProductTemplateRead:
            current = self._one(session, "SELECT * FROM product_templates WHERE id = :id", {"id": template_id})
            if not current:
                raise business_error(404, "PRODUCT_TEMPLATE_NOT_FOUND", "Product template not found.")
            values = {**current, **payload.model_dump(exclude_unset=True), "id": template_id}
            row = self._one(session, "UPDATE product_templates SET title=:title, brand=:brand, category=:category, description=:description, default_market=:default_market, status=:status, updated_at=now() WHERE id=:id RETURNING *", values)
            return ProductTemplateRead(**row)

        return self._write(run)

    def delete_product_template(self, template_id: UUID) -> None:
        def run(session: Session) -> None:
            self._exec(session, "DELETE FROM product_templates WHERE id = :id", {"id": template_id})

        return self._write(run)

    def list_skus(self) -> list[SkuRead]:
        return self._read(lambda session: [SkuRead(**row) for row in self._all(session, "SELECT * FROM skus ORDER BY sku_code")])

    def get_sku(self, sku_id: UUID) -> SkuRead:
        def run(session: Session) -> SkuRead:
            row = self._one(session, "SELECT * FROM skus WHERE id = :id", {"id": sku_id})
            if not row:
                raise business_error(404, "SKU_NOT_FOUND", "SKU not found.")
            return SkuRead(**row)

        return self._read(run)

    def create_sku(self, payload: SkuCreate) -> SkuRead:
        return self._write(lambda session: SkuRead(**self._one(session, "INSERT INTO skus (sku_code, product_template_id, title, market, price, hero_image_url, status) VALUES (:sku_code, :product_template_id, :title, :market, :price, :hero_image_url, :status) RETURNING *", payload.model_dump())))

    def update_sku(self, sku_id: UUID, payload: SkuUpdate) -> SkuRead:
        def run(session: Session) -> SkuRead:
            current = self._one(session, "SELECT * FROM skus WHERE id = :id", {"id": sku_id})
            if not current:
                raise business_error(404, "SKU_NOT_FOUND", "SKU not found.")
            values = {**current, **payload.model_dump(exclude_unset=True), "id": sku_id}
            row = self._one(session, "UPDATE skus SET title=:title, market=:market, price=:price, hero_image_url=:hero_image_url, status=:status, updated_at=now() WHERE id=:id RETURNING *", values)
            return SkuRead(**row)

        return self._write(run)

    def delete_sku(self, sku_id: UUID) -> None:
        return self._write(lambda session: self._exec(session, "DELETE FROM skus WHERE id = :id", {"id": sku_id}))

    def list_warehouses(self) -> list[WarehouseRead]:
        return self._read(
            lambda session: [
                WarehouseRead(**row)
                for row in self._all(
                    session,
                    "SELECT * FROM warehouses ORDER BY CASE WHEN warehouse_code = 'US_WEST' THEN 0 ELSE 1 END, created_at, warehouse_code",
                )
            ]
        )

    def create_warehouse(self, payload: WarehouseCreate) -> WarehouseRead:
        return self._write(lambda session: WarehouseRead(**self._one(session, "INSERT INTO warehouses (warehouse_code, name, country, region, status) VALUES (:warehouse_code, :name, :country, :region, :status) RETURNING *", payload.model_dump())))

    def update_warehouse(self, warehouse_id: UUID, payload: WarehouseUpdate) -> WarehouseRead:
        def run(session: Session) -> WarehouseRead:
            current = self._one(session, "SELECT * FROM warehouses WHERE id = :id", {"id": warehouse_id})
            if not current:
                raise business_error(404, "WAREHOUSE_NOT_FOUND", "Warehouse not found.")
            values = {**current, **payload.model_dump(exclude_unset=True), "id": warehouse_id}
            row = self._one(session, "UPDATE warehouses SET name=:name, country=:country, region=:region, status=:status, updated_at=now() WHERE id=:id RETURNING *", values)
            return WarehouseRead(**row)

        return self._write(run)

    def list_suppliers(self) -> list[SupplierRead]:
        return self._read(lambda session: [SupplierRead(**row) for row in self._all(session, "SELECT * FROM suppliers ORDER BY supplier_code")])

    def create_supplier(self, payload: SupplierCreate) -> SupplierRead:
        return self._write(lambda session: SupplierRead(**self._one(session, "INSERT INTO suppliers (supplier_code, name, contact_email, status) VALUES (:supplier_code, :name, :contact_email, :status) RETURNING *", payload.model_dump())))

    def list_channel_accounts(self) -> list[ChannelAccountRead]:
        return self._read(lambda session: [ChannelAccountRead(**row) for row in self._all(session, "SELECT * FROM channel_accounts ORDER BY account_name")])

    def create_channel_account(self, payload: ChannelAccountCreate) -> ChannelAccountRead:
        return self._write(lambda session: ChannelAccountRead(**self._one(session, "INSERT INTO channel_accounts (channel, account_name, market, status, credentials_ref) VALUES (:channel, :account_name, :market, :status, :credentials_ref) RETURNING *", payload.model_dump())))

    def list_channel_listings(self) -> list[ChannelListingRead]:
        return self._read(lambda session: [ChannelListingRead(**row) for row in self._all(session, "SELECT * FROM channel_listings ORDER BY external_listing_id")])

    def create_channel_listing(self, payload: ChannelListingCreate) -> ChannelListingRead:
        def run(session: Session) -> ChannelListingRead:
            row = self._one(session, "INSERT INTO channel_listings (sku_id, channel_account_id, external_listing_id, external_sku, title, price, status) VALUES (:sku_id, :channel_account_id, :external_listing_id, :external_sku, :title, :price, :status) RETURNING *", payload.model_dump())
            self._outbox(session, "channel_listing.changed", "channel_listing", row["id"], row)
            return ChannelListingRead(**row)

        return self._write(run)

    def list_inventory_policies(self) -> list[InventoryPolicyRead]:
        return self._read(lambda session: [InventoryPolicyRead(**row) for row in self._all(session, "SELECT * FROM inventory_policies ORDER BY created_at")])

    def create_inventory_policy(self, payload: InventoryPolicyCreate) -> InventoryPolicyRead:
        return self._write(lambda session: InventoryPolicyRead(**self._one(session, "INSERT INTO inventory_policies (sku_id, warehouse_id, reorder_point, reorder_qty, lead_time_days, service_level, coverage_days_target) VALUES (:sku_id, :warehouse_id, :reorder_point, :reorder_qty, :lead_time_days, :service_level, :coverage_days_target) RETURNING *", payload.model_dump())))

    def list_inventory_balances(self) -> list[InventoryBalanceRead]:
        def run(session: Session) -> list[InventoryBalanceRead]:
            rows = self._all(
                session,
                """
                SELECT ib.*
                FROM inventory_balances ib
                JOIN skus s ON s.id = ib.sku_id
                JOIN warehouses w ON w.id = ib.warehouse_id
                ORDER BY s.sku_code, CASE WHEN w.warehouse_code = 'US_WEST' THEN 0 ELSE 1 END, w.warehouse_code
                """,
            )
            return [self._balance_read(session, row) for row in rows]

        return self._read(run)

    def list_movements(self) -> list[InventoryMovementRead]:
        return self._read(lambda session: [InventoryMovementRead(**row) for row in self._all(session, "SELECT * FROM inventory_movements ORDER BY created_at")])

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
            raise business_error(400, "UNSUPPORTED_MOVEMENT_TYPE", "Unsupported movement type.")
        return self._write(
            lambda session: self._apply_inventory_delta(
                session,
                sku_id=payload.sku_id,
                warehouse_id=payload.warehouse_id,
                movement_type=movement_type,
                quantity=payload.quantity,
                on_hand_delta=deltas[movement_type][0],
                allocated_delta=deltas[movement_type][1],
                damaged_delta=deltas[movement_type][2],
                quarantine_delta=deltas[movement_type][3],
                source_type="inventory_command",
                source_id=None,
                reason=payload.reason,
                idempotency_key=payload.idempotency_key,
            )
        )

    def adjust_inventory(self, payload: InventoryAdjustmentCommand) -> InventoryAdjustmentRead:
        def run(session: Session) -> InventoryAdjustmentRead:
            existing = self._one(session, "SELECT * FROM inventory_adjustments WHERE idempotency_key = :key", {"key": payload.idempotency_key})
            if existing:
                return InventoryAdjustmentRead(**existing)
            status = "pending" if abs(payload.quantity_delta) >= HIGH_RISK_ADJUSTMENT_THRESHOLD else "applied"
            adjustment = self._one(
                session,
                """
                INSERT INTO inventory_adjustments (adjustment_number, sku_id, warehouse_id, quantity_delta, reason, status, idempotency_key)
                VALUES (:adjustment_number, :sku_id, :warehouse_id, :quantity_delta, :reason, :status, :idempotency_key)
                RETURNING *
                """,
                {
                    "adjustment_number": f"ADJ-{now_utc().strftime('%Y%m%d%H%M%S%f')}",
                    "sku_id": payload.sku_id,
                    "warehouse_id": payload.warehouse_id,
                    "quantity_delta": payload.quantity_delta,
                    "reason": payload.reason,
                    "status": status,
                    "idempotency_key": payload.idempotency_key,
                },
            )
            if status == "pending":
                approval = self._one(
                    session,
                    "INSERT INTO approval_requests (request_type, source_type, source_id, status, requested_at, reason) VALUES ('inventory_adjustment', 'inventory_adjustment', :source_id, 'pending', now(), :reason) RETURNING *",
                    {"source_id": adjustment["id"], "reason": payload.reason},
                )
                adjustment = self._one(session, "UPDATE inventory_adjustments SET approval_request_id = :approval_id WHERE id = :id RETURNING *", {"approval_id": approval["id"], "id": adjustment["id"]})
            else:
                self._apply_inventory_delta(
                    session,
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
            return InventoryAdjustmentRead(**adjustment)

        return self._write(run)

    def _lines_for(self, session: Session, table: str, fk: str, value: UUID) -> list[dict[str, Any]]:
        return self._all(session, f"SELECT * FROM {table} WHERE {fk} = :value ORDER BY created_at", {"value": value})

    def _sales_order_read(self, session: Session, order: dict[str, Any]) -> SalesOrderRead:
        payload = dict(order)
        payload["lines"] = self._lines_for(session, "sales_order_lines", "sales_order_id", order["id"])
        return SalesOrderRead(**payload)

    def list_sales_orders(self) -> list[SalesOrderRead]:
        return self._read(lambda session: [self._sales_order_read(session, row) for row in self._all(session, "SELECT * FROM sales_orders ORDER BY created_at")])

    def create_sales_order(self, payload: SalesOrderCreate) -> SalesOrderRead:
        def run(session: Session) -> SalesOrderRead:
            existing = self._one(session, "SELECT * FROM sales_orders WHERE idempotency_key = :key", {"key": payload.idempotency_key})
            if existing:
                return self._sales_order_read(session, existing)
            order = self._one(session, "INSERT INTO sales_orders (order_number, channel_account_id, status, customer_ref, idempotency_key) VALUES (:order_number, :channel_account_id, 'reserved', :customer_ref, :idempotency_key) RETURNING *", payload.model_dump(exclude={"lines"}))
            for line in payload.lines:
                line_row = self._one(session, "INSERT INTO sales_order_lines (sales_order_id, sku_id, warehouse_id, quantity, status) VALUES (:sales_order_id, :sku_id, :warehouse_id, :quantity, 'reserved') RETURNING *", {"sales_order_id": order["id"], **line.model_dump()})
                self._apply_inventory_delta(session, sku_id=line.sku_id, warehouse_id=line.warehouse_id, movement_type="allocate", quantity=line.quantity, on_hand_delta=0, allocated_delta=line.quantity, damaged_delta=0, quarantine_delta=0, source_type="sales_order", source_id=order["id"], reason=f"reserve {payload.order_number}", idempotency_key=f"{payload.idempotency_key}:allocate:{line_row['id']}")
            return self._sales_order_read(session, order)

        return self._write(run)

    def cancel_sales_order(self, order_id: UUID) -> SalesOrderRead:
        def run(session: Session) -> SalesOrderRead:
            order = self._one(session, "SELECT * FROM sales_orders WHERE id = :id FOR UPDATE", {"id": order_id})
            if not order:
                raise business_error(404, "SALES_ORDER_NOT_FOUND", "Sales order not found.")
            for line in self._lines_for(session, "sales_order_lines", "sales_order_id", order_id):
                if line["status"] == "reserved":
                    self._apply_inventory_delta(session, sku_id=line["sku_id"], warehouse_id=line["warehouse_id"], movement_type="release", quantity=line["quantity"], on_hand_delta=0, allocated_delta=-line["quantity"], damaged_delta=0, quarantine_delta=0, source_type="sales_order", source_id=order_id, reason=f"cancel {order['order_number']}", idempotency_key=f"{order['idempotency_key']}:cancel:{line['id']}")
                    self._exec(session, "UPDATE sales_order_lines SET status = 'cancelled', updated_at = now() WHERE id = :id", {"id": line["id"]})
            order = self._one(session, "UPDATE sales_orders SET status = 'cancelled', updated_at = now() WHERE id = :id RETURNING *", {"id": order_id})
            return self._sales_order_read(session, order)

        return self._write(run)

    def ship_sales_order(self, order_id: UUID) -> SalesOrderRead:
        def run(session: Session) -> SalesOrderRead:
            order = self._one(session, "SELECT * FROM sales_orders WHERE id = :id FOR UPDATE", {"id": order_id})
            if not order:
                raise business_error(404, "SALES_ORDER_NOT_FOUND", "Sales order not found.")
            for line in self._lines_for(session, "sales_order_lines", "sales_order_id", order_id):
                if line["status"] == "reserved":
                    self._apply_inventory_delta(session, sku_id=line["sku_id"], warehouse_id=line["warehouse_id"], movement_type="ship", quantity=line["quantity"], on_hand_delta=-line["quantity"], allocated_delta=-line["quantity"], damaged_delta=0, quarantine_delta=0, source_type="sales_order", source_id=order_id, reason=f"ship {order['order_number']}", idempotency_key=f"{order['idempotency_key']}:ship:{line['id']}")
                    self._exec(session, "UPDATE sales_order_lines SET status = 'shipped', updated_at = now() WHERE id = :id", {"id": line["id"]})
            order = self._one(session, "UPDATE sales_orders SET status = 'shipped', updated_at = now() WHERE id = :id RETURNING *", {"id": order_id})
            return self._sales_order_read(session, order)

        return self._write(run)

    def _purchase_order_read(self, session: Session, order: dict[str, Any]) -> PurchaseOrderRead:
        payload = dict(order)
        payload["lines"] = self._lines_for(session, "purchase_order_lines", "purchase_order_id", order["id"])
        return PurchaseOrderRead(**payload)

    def list_purchase_orders(self) -> list[PurchaseOrderRead]:
        return self._read(lambda session: [self._purchase_order_read(session, row) for row in self._all(session, "SELECT * FROM purchase_orders ORDER BY created_at")])

    def create_purchase_order(self, payload: PurchaseOrderCreate) -> PurchaseOrderRead:
        def run(session: Session) -> PurchaseOrderRead:
            existing = self._one(session, "SELECT * FROM purchase_orders WHERE idempotency_key = :key", {"key": payload.idempotency_key})
            if existing:
                return self._purchase_order_read(session, existing)
            order = self._one(session, "INSERT INTO purchase_orders (po_number, supplier_id, warehouse_id, status, expected_arrival_at, idempotency_key) VALUES (:po_number, :supplier_id, :warehouse_id, 'submitted', :expected_arrival_at, :idempotency_key) RETURNING *", payload.model_dump(exclude={"lines"}))
            for line in payload.lines:
                self._one(session, "INSERT INTO purchase_order_lines (purchase_order_id, sku_id, ordered_qty, received_qty) VALUES (:purchase_order_id, :sku_id, :ordered_qty, 0) RETURNING *", {"purchase_order_id": order["id"], **line.model_dump()})
                balance = self._balance(session, line.sku_id, payload.warehouse_id, lock=True)
                self._exec(session, "UPDATE inventory_balances SET inbound = inbound + :qty, updated_at = now() WHERE id = :id", {"qty": line.ordered_qty, "id": balance["id"]})
            return self._purchase_order_read(session, order)

        return self._write(run)

    def submit_purchase_order(self, order_id: UUID) -> PurchaseOrderRead:
        return self._write(lambda session: self._purchase_order_read(session, self._one(session, "UPDATE purchase_orders SET status = 'submitted', updated_at = now() WHERE id = :id RETURNING *", {"id": order_id})))

    def cancel_purchase_order(self, order_id: UUID) -> PurchaseOrderRead:
        def run(session: Session) -> PurchaseOrderRead:
            order = self._one(session, "UPDATE purchase_orders SET status = 'cancelled', updated_at = now() WHERE id = :id RETURNING *", {"id": order_id})
            if not order:
                raise business_error(404, "PURCHASE_ORDER_NOT_FOUND", "Purchase order not found.")
            for line in self._lines_for(session, "purchase_order_lines", "purchase_order_id", order_id):
                balance = self._balance(session, line["sku_id"], order["warehouse_id"], lock=True)
                remaining = line["ordered_qty"] - line["received_qty"]
                self._exec(session, "UPDATE inventory_balances SET inbound = GREATEST(0, inbound - :qty), updated_at = now() WHERE id = :id", {"qty": remaining, "id": balance["id"]})
            return self._purchase_order_read(session, order)

        return self._write(run)

    def _receipt_read(self, session: Session, receipt: dict[str, Any]) -> ReceiptRead:
        payload = dict(receipt)
        payload["lines"] = self._lines_for(session, "receipt_lines", "receipt_id", receipt["id"])
        return ReceiptRead(**payload)

    def list_receipts(self) -> list[ReceiptRead]:
        return self._read(lambda session: [self._receipt_read(session, row) for row in self._all(session, "SELECT * FROM receipts ORDER BY created_at")])

    def create_receipt(self, payload: ReceiptCreate) -> ReceiptRead:
        def run(session: Session) -> ReceiptRead:
            existing = self._one(session, "SELECT * FROM receipts WHERE idempotency_key = :key", {"key": payload.idempotency_key})
            if existing:
                return self._receipt_read(session, existing)
            receipt = self._one(session, "INSERT INTO receipts (receipt_number, purchase_order_id, warehouse_id, status, received_at, idempotency_key) VALUES (:receipt_number, :purchase_order_id, :warehouse_id, 'received', now(), :idempotency_key) RETURNING *", payload.model_dump(exclude={"lines"}))
            for line in payload.lines:
                self._one(session, "INSERT INTO receipt_lines (receipt_id, purchase_order_line_id, sku_id, quantity, condition) VALUES (:receipt_id, :purchase_order_line_id, :sku_id, :quantity, :condition) RETURNING *", {"receipt_id": receipt["id"], **line.model_dump()})
                damaged_delta = line.quantity if line.condition == "damaged" else 0
                quarantine_delta = line.quantity if line.condition == "quarantine" else 0
                self._apply_inventory_delta(session, sku_id=line.sku_id, warehouse_id=payload.warehouse_id, movement_type="damage" if line.condition == "damaged" else "receive", quantity=line.quantity, on_hand_delta=line.quantity, allocated_delta=0, damaged_delta=damaged_delta, quarantine_delta=quarantine_delta, source_type="receipt", source_id=receipt["id"], reason=f"receipt {payload.receipt_number}", idempotency_key=f"{payload.idempotency_key}:receipt:{line.sku_id}")
                balance = self._balance(session, line.sku_id, payload.warehouse_id, lock=True)
                self._exec(session, "UPDATE inventory_balances SET inbound = GREATEST(0, inbound - :qty), updated_at = now() WHERE id = :id", {"qty": line.quantity, "id": balance["id"]})
            return self._receipt_read(session, receipt)

        return self._write(run)

    def _transfer_read(self, session: Session, transfer: dict[str, Any]) -> StockTransferRead:
        payload = dict(transfer)
        payload["lines"] = self._lines_for(session, "stock_transfer_lines", "stock_transfer_id", transfer["id"])
        return StockTransferRead(**payload)

    def list_stock_transfers(self) -> list[StockTransferRead]:
        return self._read(lambda session: [self._transfer_read(session, row) for row in self._all(session, "SELECT * FROM stock_transfers ORDER BY created_at")])

    def create_stock_transfer(self, payload: StockTransferCreate) -> StockTransferRead:
        def run(session: Session) -> StockTransferRead:
            existing = self._one(session, "SELECT * FROM stock_transfers WHERE idempotency_key = :key", {"key": payload.idempotency_key})
            if existing:
                return self._transfer_read(session, existing)
            transfer = self._one(session, "INSERT INTO stock_transfers (transfer_number, from_warehouse_id, to_warehouse_id, status, idempotency_key) VALUES (:transfer_number, :from_warehouse_id, :to_warehouse_id, 'submitted', :idempotency_key) RETURNING *", payload.model_dump(exclude={"lines"}))
            for line in payload.lines:
                line_row = self._one(session, "INSERT INTO stock_transfer_lines (stock_transfer_id, sku_id, quantity, shipped_qty, received_qty) VALUES (:stock_transfer_id, :sku_id, :quantity, 0, 0) RETURNING *", {"stock_transfer_id": transfer["id"], **line.model_dump()})
                self._apply_inventory_delta(session, sku_id=line.sku_id, warehouse_id=payload.from_warehouse_id, movement_type="allocate", quantity=line.quantity, on_hand_delta=0, allocated_delta=line.quantity, damaged_delta=0, quarantine_delta=0, source_type="stock_transfer", source_id=transfer["id"], reason=f"reserve transfer {payload.transfer_number}", idempotency_key=f"{payload.idempotency_key}:submit:{line_row['id']}")
                balance = self._balance(session, line.sku_id, payload.to_warehouse_id, lock=True)
                self._exec(session, "UPDATE inventory_balances SET inbound = inbound + :qty, updated_at = now() WHERE id = :id", {"qty": line.quantity, "id": balance["id"]})
            return self._transfer_read(session, transfer)

        return self._write(run)

    def submit_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        return self._write(lambda session: self._transfer_read(session, self._one(session, "UPDATE stock_transfers SET status='submitted', updated_at=now() WHERE id=:id RETURNING *", {"id": transfer_id})))

    def ship_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        def run(session: Session) -> StockTransferRead:
            transfer = self._one(session, "SELECT * FROM stock_transfers WHERE id = :id FOR UPDATE", {"id": transfer_id})
            if not transfer:
                raise business_error(404, "STOCK_TRANSFER_NOT_FOUND", "Stock transfer not found.")
            for line in self._lines_for(session, "stock_transfer_lines", "stock_transfer_id", transfer_id):
                if line["shipped_qty"] == 0:
                    self._apply_inventory_delta(session, sku_id=line["sku_id"], warehouse_id=transfer["from_warehouse_id"], movement_type="transfer_out", quantity=line["quantity"], on_hand_delta=-line["quantity"], allocated_delta=-line["quantity"], damaged_delta=0, quarantine_delta=0, source_type="stock_transfer", source_id=transfer_id, reason=f"ship transfer {transfer['transfer_number']}", idempotency_key=f"{transfer['idempotency_key']}:ship:{line['id']}")
                    self._exec(session, "UPDATE stock_transfer_lines SET shipped_qty = quantity, updated_at=now() WHERE id=:id", {"id": line["id"]})
            transfer = self._one(session, "UPDATE stock_transfers SET status='in_transit', updated_at=now() WHERE id=:id RETURNING *", {"id": transfer_id})
            return self._transfer_read(session, transfer)

        return self._write(run)

    def receive_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        def run(session: Session) -> StockTransferRead:
            transfer = self._one(session, "SELECT * FROM stock_transfers WHERE id = :id FOR UPDATE", {"id": transfer_id})
            if not transfer:
                raise business_error(404, "STOCK_TRANSFER_NOT_FOUND", "Stock transfer not found.")
            for line in self._lines_for(session, "stock_transfer_lines", "stock_transfer_id", transfer_id):
                if line["received_qty"] == 0:
                    self._apply_inventory_delta(session, sku_id=line["sku_id"], warehouse_id=transfer["to_warehouse_id"], movement_type="transfer_in", quantity=line["quantity"], on_hand_delta=line["quantity"], allocated_delta=0, damaged_delta=0, quarantine_delta=0, source_type="stock_transfer", source_id=transfer_id, reason=f"receive transfer {transfer['transfer_number']}", idempotency_key=f"{transfer['idempotency_key']}:receive:{line['id']}")
                    balance = self._balance(session, line["sku_id"], transfer["to_warehouse_id"], lock=True)
                    self._exec(session, "UPDATE inventory_balances SET inbound = GREATEST(0, inbound - :qty), updated_at=now() WHERE id=:id", {"qty": line["quantity"], "id": balance["id"]})
                    self._exec(session, "UPDATE stock_transfer_lines SET received_qty = quantity, updated_at=now() WHERE id=:id", {"id": line["id"]})
            transfer = self._one(session, "UPDATE stock_transfers SET status='received', updated_at=now() WHERE id=:id RETURNING *", {"id": transfer_id})
            return self._transfer_read(session, transfer)

        return self._write(run)

    def cancel_stock_transfer(self, transfer_id: UUID) -> StockTransferRead:
        return self._write(lambda session: self._transfer_read(session, self._one(session, "UPDATE stock_transfers SET status='cancelled', updated_at=now() WHERE id=:id RETURNING *", {"id": transfer_id})))

    def list_adjustments(self) -> list[InventoryAdjustmentRead]:
        return self._read(lambda session: [InventoryAdjustmentRead(**row) for row in self._all(session, "SELECT * FROM inventory_adjustments ORDER BY created_at")])

    def submit_adjustment(self, adjustment_id: UUID) -> InventoryAdjustmentRead:
        return self._read(lambda session: InventoryAdjustmentRead(**self._one(session, "SELECT * FROM inventory_adjustments WHERE id = :id", {"id": adjustment_id})))

    def apply_adjustment(self, adjustment_id: UUID) -> InventoryAdjustmentRead:
        def run(session: Session) -> InventoryAdjustmentRead:
            adjustment = self._one(session, "SELECT * FROM inventory_adjustments WHERE id = :id", {"id": adjustment_id})
            if not adjustment:
                raise business_error(404, "INVENTORY_ADJUSTMENT_NOT_FOUND", "Inventory adjustment not found.")
            if adjustment["status"] == "pending":
                raise business_error(400, "APPROVAL_REQUIRED", "Pending adjustment requires approval before apply.")
            return InventoryAdjustmentRead(**adjustment)

        return self._write(run)

    def _count_read(self, session: Session, count: dict[str, Any]) -> StockCountRead:
        payload = dict(count)
        payload["lines"] = self._lines_for(session, "stock_count_lines", "stock_count_id", count["id"])
        return StockCountRead(**payload)

    def list_stock_counts(self) -> list[StockCountRead]:
        return self._read(lambda session: [self._count_read(session, row) for row in self._all(session, "SELECT * FROM stock_counts ORDER BY created_at")])

    def create_stock_count(self, payload: StockCountCreate) -> StockCountRead:
        def run(session: Session) -> StockCountRead:
            count = self._one(session, "INSERT INTO stock_counts (count_number, warehouse_id, status, started_at) VALUES (:count_number, :warehouse_id, 'draft', now()) RETURNING *", payload.model_dump(exclude={"lines"}))
            for line in payload.lines:
                self._one(session, "INSERT INTO stock_count_lines (stock_count_id, sku_id, expected_qty, counted_qty, variance_qty, status) VALUES (:stock_count_id, :sku_id, :expected_qty, :counted_qty, :variance_qty, 'open') RETURNING *", {"stock_count_id": count["id"], **line.model_dump(), "variance_qty": line.counted_qty - line.expected_qty})
            return self._count_read(session, count)

        return self._write(run)

    def submit_stock_count(self, count_id: UUID) -> StockCountRead:
        return self._write(lambda session: self._count_read(session, self._one(session, "UPDATE stock_counts SET status='submitted', completed_at=now(), updated_at=now() WHERE id=:id RETURNING *", {"id": count_id})))

    def apply_stock_count(self, count_id: UUID) -> StockCountRead:
        def run(session: Session) -> StockCountRead:
            count = self._one(session, "SELECT * FROM stock_counts WHERE id = :id FOR UPDATE", {"id": count_id})
            if not count:
                raise business_error(404, "STOCK_COUNT_NOT_FOUND", "Stock count not found.")
            for line in self._lines_for(session, "stock_count_lines", "stock_count_id", count_id):
                if line["variance_qty"] != 0 and line["status"] != "applied":
                    self._apply_inventory_delta(session, sku_id=line["sku_id"], warehouse_id=count["warehouse_id"], movement_type="adjust", quantity=abs(line["variance_qty"]), on_hand_delta=line["variance_qty"], allocated_delta=0, damaged_delta=0, quarantine_delta=0, source_type="stock_count", source_id=count_id, reason=f"stock count {count['count_number']}", idempotency_key=f"stock-count:{count_id}:{line['sku_id']}")
                    self._exec(session, "UPDATE stock_count_lines SET status='applied', updated_at=now() WHERE id=:id", {"id": line["id"]})
            count = self._one(session, "UPDATE stock_counts SET status='applied', updated_at=now() WHERE id=:id RETURNING *", {"id": count_id})
            return self._count_read(session, count)

        return self._write(run)

    def list_approvals(self) -> list[ApprovalRead]:
        return self._read(lambda session: [ApprovalRead(**row) for row in self._all(session, "SELECT * FROM approval_requests ORDER BY requested_at NULLS LAST, created_at")])

    def approve(self, approval_id: UUID, payload: ApprovalDecision) -> ApprovalRead:
        def run(session: Session) -> ApprovalRead:
            approval = self._one(session, "SELECT * FROM approval_requests WHERE id = :id FOR UPDATE", {"id": approval_id})
            if not approval:
                raise business_error(404, "APPROVAL_NOT_FOUND", "Approval not found.")
            adjustment = self._one(session, "SELECT * FROM inventory_adjustments WHERE id = :id FOR UPDATE", {"id": approval["source_id"]})
            if adjustment and adjustment["status"] == "pending":
                self._apply_inventory_delta(session, sku_id=adjustment["sku_id"], warehouse_id=adjustment["warehouse_id"], movement_type="adjust", quantity=abs(adjustment["quantity_delta"]), on_hand_delta=adjustment["quantity_delta"], allocated_delta=0, damaged_delta=0, quarantine_delta=0, source_type="inventory_adjustment", source_id=adjustment["id"], reason=adjustment["reason"], idempotency_key=f"{adjustment['idempotency_key']}:approved")
                self._exec(session, "UPDATE inventory_adjustments SET status='applied', updated_at=now() WHERE id=:id", {"id": adjustment["id"]})
            row = self._one(session, "UPDATE approval_requests SET status='approved', decision_note=:note, decided_at=now(), updated_at=now() WHERE id=:id RETURNING *", {"id": approval_id, "note": payload.decision_note})
            return ApprovalRead(**row)

        return self._write(run)

    def reject(self, approval_id: UUID, payload: ApprovalDecision) -> ApprovalRead:
        def run(session: Session) -> ApprovalRead:
            approval = self._one(session, "UPDATE approval_requests SET status='rejected', decision_note=:note, decided_at=now(), updated_at=now() WHERE id=:id RETURNING *", {"id": approval_id, "note": payload.decision_note})
            if not approval:
                raise business_error(404, "APPROVAL_NOT_FOUND", "Approval not found.")
            self._exec(session, "UPDATE inventory_adjustments SET status='rejected', updated_at=now() WHERE id=:id", {"id": approval["source_id"]})
            return ApprovalRead(**approval)

        return self._write(run)

    def list_sync_jobs(self) -> list[dict[str, Any]]:
        return self._read(lambda session: self._all(session, "SELECT * FROM inventory_sync_jobs ORDER BY created_at"))

    def create_sync_job(self) -> dict[str, Any]:
        def run(session: Session) -> dict[str, Any]:
            pending = self._one(session, "SELECT count(*)::int AS count FROM outbox_events WHERE status = 'pending'")["count"]
            account = self._one(session, "SELECT id FROM channel_accounts ORDER BY created_at LIMIT 1")
            job = self._one(session, "INSERT INTO inventory_sync_jobs (channel_account_id, status, started_at, finished_at, summary) VALUES (:account_id, 'succeeded', now(), now(), CAST(:summary AS jsonb)) RETURNING *", {"account_id": account["id"] if account else None, "summary": self._json({"pending_events": pending})})
            self._exec(session, "UPDATE outbox_events SET status='sent', processed_at=now() WHERE status='pending'")
            return job

        return self._write(run)

    def list_audit_logs(self) -> list[AuditLogRead]:
        return self._read(lambda session: [AuditLogRead(**row) for row in self._all(session, "SELECT * FROM audit_logs ORDER BY created_at")])
