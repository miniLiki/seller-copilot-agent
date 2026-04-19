from __future__ import annotations

import pytest
from fastapi import HTTPException

from tools.platform_store import store
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
    SkuUpdate,
    StockTransferCreate,
    StockTransferLineCreate,
    WarehouseCreate,
)


def setup_function() -> None:
    store.reset()


def _first_sku_and_warehouse():
    return store.list_skus()[0], store.list_warehouses()[0]


def test_legacy_product_and_inventory_aggregate_from_new_model() -> None:
    product = store.legacy_product("SKU_001")
    inventory = store.legacy_inventory("SKU_001")

    assert product is not None
    assert product.product_id == "SKU_001"
    assert product.inventory == 124
    assert inventory is not None
    assert inventory.safety_stock == 60
    assert inventory.risk_level == "low"


def test_sku_crud_uses_uuid_id_and_unique_business_key() -> None:
    template_id = store.list_product_templates()[0].id
    created = store.create_sku(
        SkuCreate(
            sku_code="SKU_TEST",
            product_template_id=template_id,
            title="Test SKU",
            market="US",
            price=12.5,
            hero_image_url="data/images/sku_test.jpg",
        )
    )
    assert str(created.id) != "SKU_TEST"

    with pytest.raises(HTTPException) as exc_info:
        store.create_sku(
            SkuCreate(
                sku_code="SKU_TEST",
                product_template_id=template_id,
                title="Test SKU 2",
                market="US",
                price=13,
                hero_image_url="data/images/sku_test_2.jpg",
            )
        )
    assert exc_info.value.status_code == 409

    updated = store.update_sku(created.id, SkuUpdate(price=15.25, status="draft"))
    assert updated.price == 15.25
    assert updated.status == "draft"


def test_inventory_receive_allocate_release_ship_and_idempotency() -> None:
    sku, warehouse = _first_sku_and_warehouse()
    before = store.list_inventory_balances()[0]

    receive = store.inventory_command(
        "receive",
        InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=10, reason="test receive", idempotency_key="rcv-1"),
    )
    duplicate_receive = store.inventory_command(
        "receive",
        InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=10, reason="test receive", idempotency_key="rcv-1"),
    )
    assert duplicate_receive.id == receive.id

    store.inventory_command("allocate", InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=5, reason="test allocate", idempotency_key="alloc-1"))
    store.inventory_command("release", InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=2, reason="test release", idempotency_key="rel-1"))
    store.inventory_command("ship", InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=3, reason="test ship", idempotency_key="ship-1"))

    after = store.list_inventory_balances()[0]
    assert after.on_hand == before.on_hand + 7
    assert after.allocated == before.allocated
    assert after.available_to_sell == before.available_to_sell + 7
    assert len(store.list_movements()) >= 5


def test_insufficient_stock_returns_business_error() -> None:
    sku, warehouse = _first_sku_and_warehouse()
    with pytest.raises(HTTPException) as exc_info:
        store.inventory_command(
            "ship",
            InventoryCommand(sku_id=sku.id, warehouse_id=warehouse.id, quantity=9999, reason="oversell", idempotency_key="ship-too-much"),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INSUFFICIENT_AVAILABLE_STOCK"


def test_sales_order_reserve_cancel_and_ship() -> None:
    sku, warehouse = _first_sku_and_warehouse()
    order = store.create_sales_order(
        SalesOrderCreate(
            order_number="SO-001",
            idempotency_key="so-001",
            lines=[SalesOrderLineCreate(sku_id=sku.id, warehouse_id=warehouse.id, quantity=4)],
        )
    )
    assert order.status == "reserved"
    assert store.cancel_sales_order(order.id).status == "cancelled"

    order_2 = store.create_sales_order(
        SalesOrderCreate(
            order_number="SO-002",
            idempotency_key="so-002",
            lines=[SalesOrderLineCreate(sku_id=sku.id, warehouse_id=warehouse.id, quantity=3)],
        )
    )
    assert store.ship_sales_order(order_2.id).status == "shipped"


def test_purchase_receipt_transfer_adjustment_approval_and_sync() -> None:
    sku, warehouse = _first_sku_and_warehouse()
    supplier = store.list_suppliers()[0]
    po = store.create_purchase_order(
        PurchaseOrderCreate(
            po_number="PO-001",
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            idempotency_key="po-001",
            lines=[PurchaseOrderLineCreate(sku_id=sku.id, ordered_qty=20)],
        )
    )
    assert po.status == "submitted"
    assert store.list_inventory_balances()[0].inbound >= 20

    receipt = store.create_receipt(
        ReceiptCreate(
            receipt_number="RCPT-001",
            purchase_order_id=po.id,
            warehouse_id=warehouse.id,
            idempotency_key="receipt-001",
            lines=[ReceiptLineCreate(sku_id=sku.id, quantity=8, condition="sellable")],
        )
    )
    assert receipt.status == "received"

    destination = store.create_warehouse(WarehouseCreate(warehouse_code="US_EAST", name="US East", country="US", region="EAST"))
    transfer = store.create_stock_transfer(
        StockTransferCreate(
            transfer_number="TR-001",
            from_warehouse_id=warehouse.id,
            to_warehouse_id=destination.id,
            idempotency_key="tr-001",
            lines=[StockTransferLineCreate(sku_id=sku.id, quantity=5)],
        )
    )
    assert store.ship_stock_transfer(transfer.id).status == "in_transit"
    assert store.receive_stock_transfer(transfer.id).status == "received"

    adjustment = store.adjust_inventory(
        InventoryAdjustmentCommand(
            sku_id=sku.id,
            warehouse_id=warehouse.id,
            quantity_delta=75,
            reason="cycle variance",
            idempotency_key="adj-approval",
        )
    )
    assert adjustment.status == "pending"
    approval = store.list_approvals()[0]
    assert store.approve(approval.id, ApprovalDecision(decision_note="approved")).status == "approved"

    sync_job = store.create_sync_job()
    assert sync_job["summary"]["pending_events"] > 0
    assert len(store.list_audit_logs()) > 0
