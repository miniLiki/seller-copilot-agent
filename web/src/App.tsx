import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Boxes, ClipboardList, FileClock, PackagePlus, RefreshCw, Search, Send, Shuffle, SlidersHorizontal, Warehouse as WarehouseIcon } from "lucide-react";
import { api, InventoryBalance, InventoryMovement, ProductTemplate, Sku, Warehouse } from "./api/client";

type PageKey = "catalog" | "overview" | "warehouses" | "movements" | "purchasing" | "transfers" | "counts" | "adjustments" | "sync";

const pages: Array<{ key: PageKey; label: string; icon: JSX.Element }> = [
  { key: "catalog", label: "Catalog", icon: <Boxes size={18} /> },
  { key: "overview", label: "Inventory", icon: <Search size={18} /> },
  { key: "warehouses", label: "Warehouses", icon: <WarehouseIcon size={18} /> },
  { key: "movements", label: "Movements", icon: <FileClock size={18} /> },
  { key: "purchasing", label: "Purchasing", icon: <PackagePlus size={18} /> },
  { key: "transfers", label: "Transfers", icon: <Shuffle size={18} /> },
  { key: "counts", label: "Counts", icon: <ClipboardList size={18} /> },
  { key: "adjustments", label: "Adjustments", icon: <SlidersHorizontal size={18} /> },
  { key: "sync", label: "Sync", icon: <Send size={18} /> }
];

function Field(props: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="field">
      <span>{props.label}</span>
      <input type={props.type ?? "text"} value={props.value} onChange={(event) => props.onChange(event.target.value)} />
    </label>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: Array<Array<string | number | JSX.Element>> }) {
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function App() {
  const [page, setPage] = useState<PageKey>("overview");
  const [templates, setTemplates] = useState<ProductTemplate[]>([]);
  const [skus, setSkus] = useState<Sku[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [balances, setBalances] = useState<InventoryBalance[]>([]);
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<any[]>([]);
  const [transfers, setTransfers] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [syncJobs, setSyncJobs] = useState<any[]>([]);
  const [error, setError] = useState<string>("");
  const [query, setQuery] = useState("");
  const [skuForm, setSkuForm] = useState({ sku_code: "", title: "", price: "0", hero_image_url: "data/images/new.jpg" });
  const [commandQty, setCommandQty] = useState("1");

  async function load() {
    setError("");
    try {
      const [nextTemplates, nextSkus, nextWarehouses, nextBalances, nextMovements, nextOrders, nextPurchaseOrders, nextTransfers, nextApprovals, nextSyncJobs] = await Promise.all([
        api<ProductTemplate[]>("/api/product-templates"),
        api<Sku[]>("/api/skus"),
        api<Warehouse[]>("/api/warehouses"),
        api<InventoryBalance[]>("/api/inventory/balances"),
        api<InventoryMovement[]>("/api/inventory/movements"),
        api<any[]>("/api/sales-orders"),
        api<any[]>("/api/purchase-orders"),
        api<any[]>("/api/stock-transfers"),
        api<any[]>("/api/approvals"),
        api<any[]>("/api/sync/jobs")
      ]);
      setTemplates(nextTemplates);
      setSkus(nextSkus);
      setWarehouses(nextWarehouses);
      setBalances(nextBalances);
      setMovements(nextMovements);
      setOrders(nextOrders);
      setPurchaseOrders(nextPurchaseOrders);
      setTransfers(nextTransfers);
      setApprovals(nextApprovals);
      setSyncJobs(nextSyncJobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const filteredSkus = useMemo(() => skus.filter((sku) => `${sku.sku_code} ${sku.title}`.toLowerCase().includes(query.toLowerCase())), [skus, query]);
  const totals = balances.reduce(
    (acc, balance) => ({
      on_hand: acc.on_hand + balance.on_hand,
      allocated: acc.allocated + balance.allocated,
      available: acc.available + balance.available_to_sell,
      inbound: acc.inbound + balance.inbound,
      damaged: acc.damaged + balance.damaged,
      quarantine: acc.quarantine + balance.quarantine
    }),
    { on_hand: 0, allocated: 0, available: 0, inbound: 0, damaged: 0, quarantine: 0 }
  );

  async function createSku() {
    if (!templates[0]) return;
    await api<Sku>("/api/skus", {
      method: "POST",
      body: JSON.stringify({
        sku_code: skuForm.sku_code,
        product_template_id: templates[0].id,
        title: skuForm.title,
        market: "US",
        price: Number(skuForm.price),
        hero_image_url: skuForm.hero_image_url,
        status: "active"
      })
    });
    setSkuForm({ sku_code: "", title: "", price: "0", hero_image_url: "data/images/new.jpg" });
    await load();
  }

  async function runInventoryCommand(kind: string) {
    const sku = skus[0];
    const warehouse = warehouses[0];
    if (!sku || !warehouse) return;
    await api(`/api/inventory/${kind}`, {
      method: "POST",
      body: JSON.stringify({
        sku_id: sku.id,
        warehouse_id: warehouse.id,
        quantity: Number(commandQty),
        reason: `${kind} from UI`,
        idempotency_key: `${kind}-${Date.now()}`
      })
    });
    await load();
  }

  async function createPurchaseOrder() {
    const sku = skus[0];
    const warehouse = warehouses[0];
    const suppliers = await api<any[]>("/api/suppliers");
    if (!sku || !warehouse || !suppliers[0]) return;
    await api("/api/purchase-orders", {
      method: "POST",
      body: JSON.stringify({
        po_number: `PO-${Date.now()}`,
        supplier_id: suppliers[0].id,
        warehouse_id: warehouse.id,
        idempotency_key: `po-${Date.now()}`,
        lines: [{ sku_id: sku.id, ordered_qty: Number(commandQty) }]
      })
    });
    await load();
  }

  async function createTransfer() {
    const sku = skus[0];
    if (!sku || warehouses.length < 2) return;
    await api("/api/stock-transfers", {
      method: "POST",
      body: JSON.stringify({
        transfer_number: `TR-${Date.now()}`,
        from_warehouse_id: warehouses[0].id,
        to_warehouse_id: warehouses[1].id,
        idempotency_key: `tr-${Date.now()}`,
        lines: [{ sku_id: sku.id, quantity: Number(commandQty) }]
      })
    });
    await load();
  }

  async function createSyncJob() {
    await api("/api/sync/jobs", { method: "POST" });
    await load();
  }

  return (
    <main className="shell">
      <aside className="nav">
        <div className="brand">Seller Copilot</div>
        {pages.map((item) => (
          <button key={item.key} className={page === item.key ? "active" : ""} onClick={() => setPage(item.key)}>
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </aside>
      <section className="content">
        <header className="topbar">
          <div>
            <h1>{pages.find((item) => item.key === page)?.label}</h1>
            <p>Inventory platform mock-first workspace</p>
          </div>
          <button className="iconButton" onClick={() => void load()} title="Refresh">
            <RefreshCw size={18} />
          </button>
        </header>
        {error && <div className="error"><AlertTriangle size={18} />{error}</div>}

        {page === "catalog" && (
          <section className="stack">
            <div className="toolbar">
              <Field label="Search" value={query} onChange={setQuery} />
              <Field label="SKU code" value={skuForm.sku_code} onChange={(value) => setSkuForm({ ...skuForm, sku_code: value })} />
              <Field label="Title" value={skuForm.title} onChange={(value) => setSkuForm({ ...skuForm, title: value })} />
              <Field label="Price" value={skuForm.price} onChange={(value) => setSkuForm({ ...skuForm, price: value })} type="number" />
              <button onClick={() => void createSku()}>Create SKU</button>
            </div>
            <Table headers={["SKU", "Title", "Market", "Price", "Status"]} rows={filteredSkus.map((sku) => [sku.sku_code, sku.title, sku.market, sku.price, sku.status])} />
          </section>
        )}

        {page === "overview" && (
          <section className="stack">
            <div className="metrics">
              {Object.entries(totals).map(([key, value]) => <div className="metric" key={key}><span>{key.replace("_", " ")}</span><strong>{value}</strong></div>)}
            </div>
            <Table headers={["SKU", "Warehouse", "On hand", "Allocated", "Available", "Inbound", "Damaged", "Quarantine", "Risk"]} rows={balances.map((b) => [b.sku_code, b.warehouse_code, b.on_hand, b.allocated, b.available_to_sell, b.inbound, b.damaged, b.quarantine, b.risk_level])} />
          </section>
        )}

        {page === "warehouses" && <Table headers={["Code", "Name", "Status"]} rows={warehouses.map((w) => [w.warehouse_code, w.name, w.status])} />}

        {page === "movements" && <Table headers={["Type", "Qty", "On hand delta", "Allocated delta", "Reason", "Created"]} rows={movements.map((m) => [m.movement_type, m.quantity, m.quantity_on_hand_delta, m.quantity_allocated_delta, m.reason ?? "", new Date(m.created_at).toLocaleString()])} />}

        {page === "purchasing" && (
          <section className="stack">
            <div className="toolbar"><Field label="Qty" value={commandQty} onChange={setCommandQty} type="number" /><button onClick={() => void createPurchaseOrder()}>Create PO</button></div>
            <Table headers={["PO", "Status", "Lines"]} rows={purchaseOrders.map((po) => [po.po_number, po.status, po.lines.length])} />
          </section>
        )}

        {page === "transfers" && (
          <section className="stack">
            <div className="toolbar"><Field label="Qty" value={commandQty} onChange={setCommandQty} type="number" /><button onClick={() => void createTransfer()}>Create Transfer</button></div>
            <Table headers={["Transfer", "Status", "Lines"]} rows={transfers.map((t) => [t.transfer_number, t.status, t.lines.length])} />
          </section>
        )}

        {page === "counts" && <Table headers={["Area", "Current support"]} rows={[["Stock counts", "API placeholder for count sessions and variance apply"], ["Orders", `${orders.length} sales orders reserved or shipped`]]} />}

        {page === "adjustments" && (
          <section className="stack">
            <div className="toolbar">
              <Field label="Qty" value={commandQty} onChange={setCommandQty} type="number" />
              {["receive", "allocate", "release", "ship", "damage", "return"].map((kind) => <button key={kind} onClick={() => void runInventoryCommand(kind)}>{kind}</button>)}
            </div>
            <Table headers={["Approval", "Type", "Status", "Reason"]} rows={approvals.map((a) => [a.id.slice(0, 8), a.request_type, a.status, a.reason ?? ""])} />
          </section>
        )}

        {page === "sync" && (
          <section className="stack">
            <div className="toolbar"><button onClick={() => void createSyncJob()}>Run Sync</button></div>
            <Table headers={["Job", "Status", "Summary"]} rows={syncJobs.map((job) => [job.id.slice(0, 8), job.status, JSON.stringify(job.summary)])} />
          </section>
        )}
      </section>
    </main>
  );
}
