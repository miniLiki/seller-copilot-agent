from __future__ import annotations

import argparse
from uuid import UUID, uuid5, NAMESPACE_DNS

from sqlalchemy import text

from .database import SessionLocal


TABLES = [
    "sync_errors",
    "inventory_sync_jobs",
    "outbox_events",
    "audit_logs",
    "stock_count_lines",
    "stock_counts",
    "inventory_adjustments",
    "approval_requests",
    "stock_transfer_lines",
    "stock_transfers",
    "receipt_lines",
    "receipts",
    "purchase_order_lines",
    "purchase_orders",
    "sales_order_lines",
    "sales_orders",
    "serial_numbers",
    "inventory_lots",
    "inventory_policies",
    "inventory_movements",
    "inventory_balances",
    "channel_listings",
    "channel_accounts",
    "suppliers",
    "bins",
    "locations",
    "warehouses",
    "skus",
    "product_templates",
    "role_permissions",
    "user_roles",
    "permissions",
    "roles",
    "users",
]

COUNT_TABLES = [
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "product_templates",
    "skus",
    "warehouses",
    "suppliers",
    "channel_accounts",
    "channel_listings",
    "inventory_policies",
    "inventory_balances",
    "inventory_movements",
    "outbox_events",
]


def stable_id(name: str) -> UUID:
    return uuid5(NAMESPACE_DNS, f"seller-copilot:{name}")


def execute(session, sql: str, params: dict | None = None) -> None:
    session.execute(text(sql), params or {})


def reset(session) -> None:
    execute(session, "TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")


def seed(session) -> None:
    users = [
        ("admin@example.com", "Admin User", "active"),
        ("inventory@example.com", "Inventory Manager", "active"),
        ("warehouse@example.com", "Warehouse Operator", "active"),
        ("viewer@example.com", "Viewer User", "active"),
    ]
    for email, display_name, status in users:
        execute(
            session,
            "INSERT INTO users (id, email, display_name, status) VALUES (:id, :email, :display_name, :status) ON CONFLICT (email) DO NOTHING",
            {"id": stable_id(email), "email": email, "display_name": display_name, "status": status},
        )

    roles = [("admin", "Admin"), ("inventory_manager", "Inventory Manager"), ("warehouse_operator", "Warehouse Operator"), ("viewer", "Viewer")]
    for role_key, name in roles:
        execute(
            session,
            "INSERT INTO roles (id, role_key, name) VALUES (:id, :role_key, :name) ON CONFLICT (role_key) DO NOTHING",
            {"id": stable_id(f"role:{role_key}"), "role_key": role_key, "name": name},
        )

    permissions = [
        "catalog.read",
        "catalog.write",
        "inventory.read",
        "inventory.adjust",
        "inventory.approve",
        "orders.write",
        "purchasing.write",
        "sync.manage",
    ]
    for permission in permissions:
        execute(
            session,
            "INSERT INTO permissions (id, permission_key, description) VALUES (:id, :permission_key, :description) ON CONFLICT (permission_key) DO NOTHING",
            {"id": stable_id(f"permission:{permission}"), "permission_key": permission, "description": permission.replace(".", " ")},
        )

    role_permission_pairs = [
        ("admin", "catalog.read"),
        ("admin", "catalog.write"),
        ("admin", "inventory.read"),
        ("admin", "inventory.adjust"),
        ("admin", "inventory.approve"),
        ("admin", "orders.write"),
        ("admin", "purchasing.write"),
        ("admin", "sync.manage"),
        ("inventory_manager", "inventory.read"),
        ("inventory_manager", "inventory.adjust"),
        ("warehouse_operator", "inventory.read"),
        ("viewer", "catalog.read"),
    ]
    for role_key, permission_key in role_permission_pairs:
        execute(
            session,
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r, permissions p
            WHERE r.role_key = :role_key AND p.permission_key = :permission_key
            ON CONFLICT DO NOTHING
            """,
            {"role_key": role_key, "permission_key": permission_key},
        )

    categories = [
        ("PT_NECK_FAN", "Portable Neck Fan", "Summer Accessories"),
        ("PT_LAPTOP_STAND", "Adjustable Laptop Stand", "Office Accessories"),
        ("PT_USB_LAMP", "USB Desk Lamp", "Office Accessories"),
        ("PT_TRAVEL_MUG", "Insulated Travel Mug", "Kitchen"),
        ("PT_PHONE_MOUNT", "Magnetic Phone Mount", "Auto Accessories"),
        ("PT_YOGA_MAT", "Foldable Yoga Mat", "Fitness"),
        ("PT_STORAGE_BOX", "Stackable Storage Box", "Home"),
        ("PT_LED_STRIP", "Smart LED Strip", "Lighting"),
        ("PT_AIR_PURIFIER", "Mini Air Purifier", "Home Appliances"),
        ("PT_BACKPACK", "Commuter Backpack", "Bags"),
    ]
    for product_code, title, category in categories:
        execute(
            session,
            """
            INSERT INTO product_templates (id, product_code, title, brand, category, description, default_market, status)
            VALUES (:id, :product_code, :title, 'DemoBrand', :category, :description, 'US', 'active')
            ON CONFLICT (product_code) DO NOTHING
            """,
            {"id": stable_id(product_code), "product_code": product_code, "title": title, "category": category, "description": f"{title} demo template."},
        )

    for index in range(1, 11):
        if index == 1:
            sku_code, title, template_code, price, image = "SKU_001", "Portable Neck Fan", "PT_NECK_FAN", 29.99, "data/images/sku_001_main.jpg"
        elif index == 2:
            sku_code, title, template_code, price, image = "SKU_002", "Adjustable Laptop Stand", "PT_LAPTOP_STAND", 39.99, "data/images/sku_002_main.jpg"
        else:
            template_code, template_title, _ = categories[(index - 1) % len(categories)]
            sku_code, title, price, image = f"SKU_{index:03d}", f"{template_title} Variant {index}", 19.99 + index, f"data/images/sku_{index:03d}_main.jpg"
        execute(
            session,
            """
            INSERT INTO skus (id, sku_code, product_template_id, title, market, price, hero_image_url, status)
            VALUES (:id, :sku_code, :product_template_id, :title, 'US', :price, :hero_image_url, 'active')
            ON CONFLICT (sku_code) DO NOTHING
            """,
            {
                "id": stable_id(sku_code),
                "sku_code": sku_code,
                "product_template_id": stable_id(template_code),
                "title": title,
                "price": price,
                "hero_image_url": image,
            },
        )

    warehouses = [("US_WEST", "US West Demo Warehouse", "US", "WEST"), ("US_EAST", "US East Demo Warehouse", "US", "EAST"), ("US_CENTRAL", "US Central Demo Warehouse", "US", "CENTRAL")]
    for code, name, country, region in warehouses:
        execute(
            session,
            "INSERT INTO warehouses (id, warehouse_code, name, country, region, status) VALUES (:id, :code, :name, :country, :region, 'active') ON CONFLICT (warehouse_code) DO NOTHING",
            {"id": stable_id(code), "code": code, "name": name, "country": country, "region": region},
        )

    for index in range(1, 6):
        execute(
            session,
            "INSERT INTO suppliers (id, supplier_code, name, contact_email, status) VALUES (:id, :code, :name, :email, 'active') ON CONFLICT (supplier_code) DO NOTHING",
            {"id": stable_id(f"SUP_{index:03d}"), "code": f"SUP_{index:03d}", "name": f"Demo Supplier {index}", "email": f"supplier{index}@example.com"},
        )

    channel_accounts = [("amazon", "Demo Amazon US", "US"), ("shopify", "Demo Shopify", "US"), ("walmart", "Demo Walmart", "US")]
    for channel, name, market in channel_accounts:
        execute(
            session,
            "INSERT INTO channel_accounts (id, channel, account_name, market, status, credentials_ref) VALUES (:id, :channel, :name, :market, 'active', NULL) ON CONFLICT DO NOTHING",
            {"id": stable_id(f"channel:{channel}"), "channel": channel, "name": name, "market": market},
        )

    for index in range(1, 11):
        execute(
            session,
            """
            INSERT INTO channel_listings (id, sku_id, channel_account_id, external_listing_id, external_sku, title, price, status)
            VALUES (:id, :sku_id, :channel_account_id, :external_listing_id, :external_sku, :title, :price, 'active')
            ON CONFLICT (channel_account_id, external_listing_id) DO NOTHING
            """,
            {
                "id": stable_id(f"listing:{index}"),
                "sku_id": stable_id(f"SKU_{index:03d}"),
                "channel_account_id": stable_id("channel:amazon" if index <= 6 else "channel:shopify"),
                "external_listing_id": f"EXT-LISTING-{index:03d}",
                "external_sku": f"SKU_{index:03d}",
                "title": f"Channel Listing {index}",
                "price": 25 + index,
            },
        )

    for index in range(1, 11):
        reorder_point = 60 if index == 1 else 40 if index == 2 else 20 + index
        execute(
            session,
            """
            INSERT INTO inventory_policies (id, sku_id, warehouse_id, reorder_point, reorder_qty, lead_time_days, service_level, coverage_days_target)
            VALUES (:id, :sku_id, :warehouse_id, :reorder_point, :reorder_qty, 14, 0.9500, 30)
            ON CONFLICT (sku_id, warehouse_id) DO NOTHING
            """,
            {
                "id": stable_id(f"policy:{index}"),
                "sku_id": stable_id(f"SKU_{index:03d}"),
                "warehouse_id": stable_id("US_WEST"),
                "reorder_point": reorder_point,
                "reorder_qty": reorder_point * 2,
            },
        )

    for index in range(1, 11):
        on_hand = 124 if index == 1 else 46 if index == 2 else 80 + index
        allocated = 0
        damaged = 0
        quarantine = 0
        execute(
            session,
            """
            INSERT INTO inventory_balances (id, sku_id, warehouse_id, on_hand, allocated, available_to_sell, inbound, damaged, quarantine, version)
            VALUES (:id, :sku_id, :warehouse_id, :on_hand, :allocated, :available_to_sell, 0, :damaged, :quarantine, 1)
            ON CONFLICT (sku_id, warehouse_id) DO NOTHING
            """,
            {
                "id": stable_id(f"balance:{index}"),
                "sku_id": stable_id(f"SKU_{index:03d}"),
                "warehouse_id": stable_id("US_WEST"),
                "on_hand": on_hand,
                "allocated": allocated,
                "available_to_sell": on_hand - allocated - damaged - quarantine,
                "damaged": damaged,
                "quarantine": quarantine,
            },
        )
        execute(
            session,
            """
            INSERT INTO inventory_movements (
              id, sku_id, warehouse_id, movement_type, quantity,
              quantity_on_hand_delta, quantity_allocated_delta, quantity_damaged_delta, quantity_quarantine_delta,
              source_type, source_id, idempotency_key, reason
            )
            VALUES (:id, :sku_id, :warehouse_id, 'receive', :quantity, :quantity, 0, 0, 0, 'seed', NULL, :idempotency_key, 'opening balance')
            ON CONFLICT (idempotency_key) DO NOTHING
            """,
            {
                "id": stable_id(f"movement:{index}"),
                "sku_id": stable_id(f"SKU_{index:03d}"),
                "warehouse_id": stable_id("US_WEST"),
                "quantity": on_hand,
                "idempotency_key": f"seed-opening-SKU_{index:03d}",
            },
        )

    execute(
        session,
        """
        INSERT INTO outbox_events (id, event_type, aggregate_type, aggregate_id, payload, status, attempts)
        VALUES (:id, 'seed.completed', 'seed', :id, '{"count": 100}'::jsonb, 'pending', 0)
        ON CONFLICT DO NOTHING
        """,
        {"id": stable_id("outbox:seed")},
    )


def row_counts(session) -> dict[str, int]:
    return {table: session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in COUNT_TABLES}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed PostgreSQL inventory platform data.")
    parser.add_argument("--reset", action="store_true", help="Truncate seeded tables before inserting.")
    parser.add_argument("--count", type=int, default=100, help="Expected cross-table seed row count.")
    args = parser.parse_args()

    if SessionLocal is None:
        raise RuntimeError("SQLAlchemy is not installed.")
    with SessionLocal.begin() as session:
        if args.reset:
            reset(session)
        seed(session)
        counts = row_counts(session)
        total = sum(counts.values())
        if total != args.count:
            raise RuntimeError(f"Expected {args.count} seeded rows, found {total}: {counts}")
        print(f"Seeded {total} rows: {counts}")


if __name__ == "__main__":
    main()
