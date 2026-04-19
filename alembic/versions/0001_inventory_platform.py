from __future__ import annotations

from alembic import op

revision = "0001_inventory_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          email text UNIQUE NOT NULL,
          display_name text NOT NULL,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS roles (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          role_key text UNIQUE NOT NULL,
          name text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS permissions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          permission_key text UNIQUE NOT NULL,
          description text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS user_roles (user_id uuid REFERENCES users(id), role_id uuid REFERENCES roles(id), PRIMARY KEY (user_id, role_id));
        CREATE TABLE IF NOT EXISTS role_permissions (role_id uuid REFERENCES roles(id), permission_id uuid REFERENCES permissions(id), PRIMARY KEY (role_id, permission_id));
        CREATE TABLE IF NOT EXISTS product_templates (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          product_code text UNIQUE NOT NULL,
          title text NOT NULL,
          brand text,
          category text NOT NULL,
          description text,
          default_market text,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS skus (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sku_code text UNIQUE NOT NULL,
          product_template_id uuid NOT NULL REFERENCES product_templates(id),
          title text NOT NULL,
          market text NOT NULL,
          price numeric(10,2) NOT NULL CHECK (price >= 0),
          hero_image_url text NOT NULL,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS warehouses (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          warehouse_code text UNIQUE NOT NULL,
          name text NOT NULL,
          country text,
          region text,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS locations (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          location_code text NOT NULL,
          name text,
          location_type text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (warehouse_id, location_code)
        );
        CREATE TABLE IF NOT EXISTS bins (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          location_id uuid NOT NULL REFERENCES locations(id),
          bin_code text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (location_id, bin_code)
        );
        CREATE TABLE IF NOT EXISTS suppliers (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          supplier_code text UNIQUE NOT NULL,
          name text NOT NULL,
          contact_email text,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS channel_accounts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          channel text NOT NULL,
          account_name text NOT NULL,
          market text NOT NULL,
          status text NOT NULL,
          credentials_ref text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS channel_listings (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sku_id uuid NOT NULL REFERENCES skus(id),
          channel_account_id uuid NOT NULL REFERENCES channel_accounts(id),
          external_listing_id text NOT NULL,
          external_sku text,
          title text,
          price numeric(10,2),
          status text NOT NULL,
          last_synced_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (channel_account_id, external_listing_id)
        );
        CREATE TABLE IF NOT EXISTS inventory_balances (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sku_id uuid NOT NULL REFERENCES skus(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          on_hand integer NOT NULL DEFAULT 0,
          allocated integer NOT NULL DEFAULT 0,
          available_to_sell integer NOT NULL DEFAULT 0,
          inbound integer NOT NULL DEFAULT 0,
          damaged integer NOT NULL DEFAULT 0,
          quarantine integer NOT NULL DEFAULT 0,
          version integer NOT NULL DEFAULT 1,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (sku_id, warehouse_id)
        );
        CREATE TABLE IF NOT EXISTS inventory_movements (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sku_id uuid NOT NULL REFERENCES skus(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          movement_type text NOT NULL,
          quantity integer NOT NULL,
          quantity_on_hand_delta integer NOT NULL DEFAULT 0,
          quantity_allocated_delta integer NOT NULL DEFAULT 0,
          quantity_damaged_delta integer NOT NULL DEFAULT 0,
          quantity_quarantine_delta integer NOT NULL DEFAULT 0,
          source_type text NOT NULL,
          source_id uuid,
          idempotency_key text UNIQUE,
          reason text,
          created_by uuid REFERENCES users(id),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS inventory_policies (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sku_id uuid NOT NULL REFERENCES skus(id),
          warehouse_id uuid REFERENCES warehouses(id),
          reorder_point integer NOT NULL,
          reorder_qty integer NOT NULL,
          lead_time_days integer NOT NULL,
          service_level numeric(5,4) NOT NULL,
          coverage_days_target integer,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (sku_id, warehouse_id)
        );
        CREATE TABLE IF NOT EXISTS inventory_lots (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sku_id uuid NOT NULL REFERENCES skus(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          lot_number text NOT NULL,
          expires_at date,
          received_at timestamptz,
          quantity integer NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (sku_id, warehouse_id, lot_number)
        );
        CREATE TABLE IF NOT EXISTS serial_numbers (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sku_id uuid NOT NULL REFERENCES skus(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          serial_number text UNIQUE NOT NULL,
          status text NOT NULL,
          source_type text,
          source_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS sales_orders (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          order_number text UNIQUE NOT NULL,
          channel_account_id uuid REFERENCES channel_accounts(id),
          status text NOT NULL,
          customer_ref text,
          idempotency_key text UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS sales_order_lines (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sales_order_id uuid NOT NULL REFERENCES sales_orders(id),
          sku_id uuid NOT NULL REFERENCES skus(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          quantity integer NOT NULL CHECK (quantity > 0),
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS purchase_orders (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          po_number text UNIQUE NOT NULL,
          supplier_id uuid NOT NULL REFERENCES suppliers(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          status text NOT NULL,
          expected_arrival_at timestamptz,
          idempotency_key text UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS purchase_order_lines (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          purchase_order_id uuid NOT NULL REFERENCES purchase_orders(id),
          sku_id uuid NOT NULL REFERENCES skus(id),
          ordered_qty integer NOT NULL,
          received_qty integer NOT NULL DEFAULT 0,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS receipts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          receipt_number text UNIQUE NOT NULL,
          purchase_order_id uuid REFERENCES purchase_orders(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          status text NOT NULL,
          received_at timestamptz NOT NULL,
          idempotency_key text UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS receipt_lines (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          receipt_id uuid NOT NULL REFERENCES receipts(id),
          purchase_order_line_id uuid REFERENCES purchase_order_lines(id),
          sku_id uuid NOT NULL REFERENCES skus(id),
          quantity integer NOT NULL CHECK (quantity > 0),
          condition text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS stock_transfers (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          transfer_number text UNIQUE NOT NULL,
          from_warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          to_warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          status text NOT NULL,
          idempotency_key text UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS stock_transfer_lines (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          stock_transfer_id uuid NOT NULL REFERENCES stock_transfers(id),
          sku_id uuid NOT NULL REFERENCES skus(id),
          quantity integer NOT NULL CHECK (quantity > 0),
          shipped_qty integer NOT NULL DEFAULT 0,
          received_qty integer NOT NULL DEFAULT 0,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS approval_requests (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          request_type text NOT NULL,
          source_type text NOT NULL,
          source_id uuid NOT NULL,
          status text NOT NULL,
          requested_by uuid REFERENCES users(id),
          approved_by uuid REFERENCES users(id),
          requested_at timestamptz,
          decided_at timestamptz,
          reason text,
          decision_note text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS inventory_adjustments (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          adjustment_number text UNIQUE NOT NULL,
          sku_id uuid NOT NULL REFERENCES skus(id),
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          quantity_delta integer NOT NULL,
          reason text NOT NULL,
          status text NOT NULL,
          approval_request_id uuid REFERENCES approval_requests(id),
          idempotency_key text UNIQUE,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS stock_counts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          count_number text UNIQUE NOT NULL,
          warehouse_id uuid NOT NULL REFERENCES warehouses(id),
          status text NOT NULL,
          started_at timestamptz,
          completed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS stock_count_lines (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          stock_count_id uuid NOT NULL REFERENCES stock_counts(id),
          sku_id uuid NOT NULL REFERENCES skus(id),
          expected_qty integer NOT NULL,
          counted_qty integer NOT NULL,
          variance_qty integer NOT NULL,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          actor_user_id uuid REFERENCES users(id),
          action text NOT NULL,
          entity_type text NOT NULL,
          entity_id uuid,
          before_json jsonb,
          after_json jsonb,
          request_id text,
          idempotency_key text,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS outbox_events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          event_type text NOT NULL,
          aggregate_type text NOT NULL,
          aggregate_id uuid NOT NULL,
          payload jsonb NOT NULL,
          status text NOT NULL,
          attempts integer NOT NULL DEFAULT 0,
          last_error text,
          created_at timestamptz NOT NULL DEFAULT now(),
          processed_at timestamptz
        );
        CREATE TABLE IF NOT EXISTS inventory_sync_jobs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          channel_account_id uuid REFERENCES channel_accounts(id),
          status text NOT NULL,
          started_at timestamptz,
          finished_at timestamptz,
          summary jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS sync_errors (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sync_job_id uuid REFERENCES inventory_sync_jobs(id),
          entity_type text NOT NULL,
          entity_id uuid,
          error_code text,
          message text NOT NULL,
          payload jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    for table in [
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
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
