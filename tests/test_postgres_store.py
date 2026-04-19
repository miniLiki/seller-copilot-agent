from __future__ import annotations

import pytest
from fastapi import HTTPException

sqlalchemy = pytest.importorskip("sqlalchemy")
text = sqlalchemy.text
SQLAlchemyError = pytest.importorskip("sqlalchemy.exc").SQLAlchemyError

from tools.database import SessionLocal
from tools.postgres_store import PostgresStore
from tools.schemas import (
    ApprovalDecision,
    InventoryAdjustmentCommand,
    InventoryCommand,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    ReceiptCreate,
    ReceiptLineCreate,
    SalesOrderCreate,
    SalesOrderLineCreate,
    SkuCreate,
    StockTransferCreate,
    StockTransferLineCreate,
    WarehouseCreate,
)
from tools.seed_postgres import COUNT_TABLES, reset, row_counts, seed


pytestmark = pytest.mark.postgres


def _database_ready() -> bool:
    if SessionLocal is None:
        return False
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


@pytest.fixture(autouse=True)
def seeded_database():
    if not _database_ready():
        pytest.skip("PostgreSQL database is not reachable")
    with SessionLocal.begin() as session:
        reset(session)
        seed(session)


def test_seed_creates_exactly_100_rows() -> None:
    with SessionLocal() as session:
        counts = row_counts(session)
    assert set(counts) == set(COUNT_TABLES)
    assert sum(counts.values()) == 100


def test_legacy_queries_read_postgres_seed() -> None:
    store = PostgresStore(SessionLocal)

    product = store.legacy_product("SKU_001")
    inventory = store.legacy_inventory("SKU_001")

    assert product is not None
    assert product.product_id == "SKU_001"
    assert product.inventory == 124
    assert inventory is not None
    assert inventory.safety_stock == 60
    assert inventory.risk_level == "low"


def test_postgres_inventory_commands_are_transactional_and_idempotent() -> None:
    store = PostgresStore(SessionLocal)
    sku = store.list_skus()[0]
    warehouse = store.list_warehouses()[0]
    before = store.list_inventory_balances()[0]

    movement = store.inventory_command(
        "receive",
        InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=7, reason="postgres receive", idempotency_key="pg-receive-1"),
    )
    duplicate = store.inventory_command(
        "receive",
        InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=7, reason="postgres receive", idempotency_key="pg-receive-1"),
    )
    after = store.list_inventory_balances()[0]

    assert duplicate.id == movement.id
    assert after.on_hand == before.on_hand + 7
    assert after.available_to_sell == before.available_to_sell + 7

    with pytest.raises(HTTPException) as exc_info:
        store.inventory_command(
            "ship",
            InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=9999, reason="oversell", idempotency_key="pg-oversell"),
        )
    assert exc_info.value.detail["error"]["code"] == "INSUFFICIENT_AVAILABLE_STOCK"


def test_postgres_order_purchase_transfer_and_approval_flows() -> None:
    store = PostgresStore(SessionLocal)
    sku = store.list_skus()[0]
    warehouse = store.list_warehouses()[0]

    order = store.create_sales_order(
        SalesOrderCreate(
            order_number="PG-SO-001",
            idempotency_key="pg-so-001",
            lines=[SalesOrderLineCreate(sku_id=sku.id, warehouse_id=warehouse.id, quantity=2)],
        )
    )
    assert order.status == "reserved"
    assert store.cancel_sales_order(order.id).status == "cancelled"

    order_2 = store.create_sales_order(
        SalesOrderCreate(
            order_number="PG-SO-002",
            idempotency_key="pg-so-002",
            lines=[SalesOrderLineCreate(sku_id=sku.id, warehouse_id=warehouse.id, quantity=2)],
        )
    )
    assert store.ship_sales_order(order_2.id).status == "shipped"

    supplier = store.list_suppliers()[0]
    po = store.create_purchase_order(
        PurchaseOrderCreate(
            po_number="PG-PO-001",
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            idempotency_key="pg-po-001",
            lines=[PurchaseOrderLineCreate(sku_id=sku.id, ordered_qty=10)],
        )
    )
    assert po.status == "submitted"
    receipt = store.create_receipt(
        ReceiptCreate(
            receipt_number="PG-RCPT-001",
            purchase_order_id=po.id,
            warehouse_id=warehouse.id,
            idempotency_key="pg-rcpt-001",
            lines=[ReceiptLineCreate(sku_id=sku.id, quantity=5, condition="sellable")],
        )
    )
    assert receipt.status == "received"

    destination = store.create_warehouse(WarehouseCreate(warehouse_code="PG_EAST", name="PG East", country="US", region="EAST"))
    transfer = store.create_stock_transfer(
        StockTransferCreate(
            transfer_number="PG-TR-001",
            from_warehouse_id=warehouse.id,
            to_warehouse_id=destination.id,
            idempotency_key="pg-tr-001",
            lines=[StockTransferLineCreate(sku_id=sku.id, quantity=3)],
        )
    )
    assert store.ship_stock_transfer(transfer.id).status == "in_transit"
    assert store.receive_stock_transfer(transfer.id).status == "received"

    adjustment = store.adjust_inventory(
        InventoryAdjustmentCommand(
            sku_id=sku.id,
            warehouse_id=warehouse.id,
            quantity_delta=75,
            reason="postgres approval",
            idempotency_key="pg-adj-approval",
        )
    )
    assert adjustment.status == "pending"
    approval = store.list_approvals()[0]
    assert store.approve(approval.id, ApprovalDecision(decision_note="postgres approved")).status == "approved"
    assert len(store.list_audit_logs()) > 0
    assert store.create_sync_job()["summary"]["pending_events"] > 0


def test_postgres_sku_crud_persists_across_sessions() -> None:
    store = PostgresStore(SessionLocal)
    template = store.list_product_templates()[0]
    created = store.create_sku(
        SkuCreate(
            sku_code="PG_SKU_TEST",
            product_template_id=template.id,
            title="Postgres SKU Test",
            market="US",
            price=12.5,
            hero_image_url="data/images/pg_sku.jpg",
        )
    )

    fresh_store = PostgresStore(SessionLocal)
    assert fresh_store.get_sku(created.id).sku_code == "PG_SKU_TEST"
