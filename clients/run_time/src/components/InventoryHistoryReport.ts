/**
 * INVENTORY HISTORY REPORT
 *
 * Fetches the inventory transactions for one inventory item (lot or unit)
 * and opens a printable HTML report in a new browser window.
 */

import { fetchInventoryTransactions, fetchStorageLocations } from "../api/runtime";
import type { InventoryTransaction, Material, MaterialLot } from "../types";

function esc(v: unknown): string {
  return String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function fmt(dt: string | null | undefined): string {
  return dt ? new Date(dt).toLocaleString() : "—";
}

function typeLabel(t: InventoryTransaction): string {
  if (t.transaction_type === "receive" && t.reference_type?.startsWith("wip_")) {
    return "Transfer to Inventory";
  }
  return t.transaction_type.charAt(0).toUpperCase() + t.transaction_type.slice(1);
}

function buildHtml(
  lot: MaterialLot,
  material: Material | undefined,
  txns: InventoryTransaction[],
  locName: (id: string | null) => string,
  generatedAt: string,
  title: string,
): string {
  const isUnit = lot.tracking_method === "unit";
  const thStyle = `style="padding:7px 10px;background:#1e3a5f;color:#fff;text-align:left;font-weight:600;font-size:12px;"`;
  const headingStyle = `style="font-size:14px;font-weight:700;color:#1e3a5f;border-bottom:2px solid #1e3a5f;padding-bottom:4px;margin-bottom:8px;"`;

  const rows = txns.length === 0
    ? `<tr><td colspan="${isUnit ? 5 : 6}" style="text-align:center;color:#9ca3af;padding:8px;">No inventory transactions recorded</td></tr>`
    : txns.map((t, i) => `
        <tr style="background:${i % 2 === 0 ? "#ffffff" : "#f9fafb"};">
          <td style="padding:6px 10px;">${fmt(t.performed_at)}</td>
          <td style="padding:6px 10px;font-weight:600;">${esc(typeLabel(t))}</td>
          <td style="padding:6px 10px;">${esc(locName(t.from_location_id))}</td>
          <td style="padding:6px 10px;">${esc(locName(t.to_location_id))}</td>
          ${isUnit ? "" : `<td style="padding:6px 10px;text-align:right;">${t.quantity}</td>`}
          <td style="padding:6px 10px;">${esc(t.reason ?? "—")}</td>
        </tr>`).join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>${esc(title)}</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; font-size: 13px; color: #111; margin: 0; padding: 24px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    td { border-bottom: 1px solid #e5e7eb; vertical-align: top; }
    h1 { font-size: 20px; color: #1e3a5f; margin: 0 0 4px; }
    .subtitle { color: #6b7280; font-size: 12px; margin-bottom: 20px; }
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; margin-bottom: 24px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px 16px; }
    .meta-item { display: flex; gap: 8px; }
    .meta-label { color: #6b7280; min-width: 100px; }
    .meta-value { font-weight: 600; }
    @media print {
      @page { margin: 1.5cm 1.8cm; size: A4; }
      body { padding: 0; font-size: 11px; }
      .no-print { display: none !important; }
      tr { page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="no-print" style="text-align:right;margin-bottom:16px;">
    <button onclick="window.print()"
      style="background:#1e3a5f;color:#fff;border:none;border-radius:6px;padding:8px 18px;font-size:13px;cursor:pointer;">
      &#128438; Print / Save as PDF
    </button>
  </div>

  <h1>Inventory History Report</h1>
  <p class="subtitle">Generated: ${esc(generatedAt)}</p>

  <div class="meta-grid">
    <div class="meta-item"><span class="meta-label">${isUnit ? "Serial #" : "Lot #"}:</span><span class="meta-value">${esc(lot.lot_number)}</span></div>
    <div class="meta-item"><span class="meta-label">Tracking:</span><span class="meta-value">${isUnit ? "Unit" : "Lot"}</span></div>
    <div class="meta-item"><span class="meta-label">Material:</span><span class="meta-value">${esc(material ? `${material.code} — ${material.name}` : lot.material_id)}</span></div>
    <div class="meta-item"><span class="meta-label">Status:</span><span class="meta-value">${esc(lot.status)}</span></div>
    ${isUnit ? "" : `<div class="meta-item"><span class="meta-label">On Hand:</span><span class="meta-value">${lot.quantity_on_hand}</span></div>`}
  </div>

  <h2 ${headingStyle}>Inventory Transactions (${txns.length})</h2>
  <table>
    <thead><tr>
      <th ${thStyle}>Date</th>
      <th ${thStyle}>Transaction</th>
      <th ${thStyle}>From</th>
      <th ${thStyle}>To</th>
      ${isUnit ? "" : `<th ${thStyle}>Quantity</th>`}
      <th ${thStyle}>Reference</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>
</body>
</html>`;
}

/** Opens a printable inventory history report for one inventory item. */
export async function printInventoryHistoryReport(
  lot: MaterialLot,
  material: Material | undefined,
): Promise<void> {
  const win = window.open("", "_blank", "width=900,height=700,scrollbars=yes");
  if (!win) {
    alert("Pop-up was blocked. Please allow pop-ups for this site and try again.");
    return;
  }
  try {
    const [txns, locations] = await Promise.all([
      fetchInventoryTransactions({ material_lot_id: lot.id, limit: 200 }),
      fetchStorageLocations(),
    ]);
    const names = new Map(locations.map((l) => [l.id, l.name]));
    const locName = (id: string | null) => (id ? names.get(id) ?? id : "—");
    const sorted = [...txns].sort(
      (a, b) => new Date(a.performed_at).getTime() - new Date(b.performed_at).getTime(),
    );
    const title = `Inventory History — ${lot.lot_number}`;
    const html = buildHtml(lot, material, sorted, locName, new Date().toLocaleString(), title);
    win.document.open();
    win.document.write(html);
    win.document.close();
    win.document.title = title;
  } catch (err) {
    win.close();
    throw err;
  }
}
