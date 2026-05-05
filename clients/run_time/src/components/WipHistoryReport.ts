/**
 * WIP HISTORY REPORT
 *
 * Fetches the genealogy record for a unit or lot and opens a printable
 * HTML report in a new browser window. The user can then print or save
 * as PDF using the browser's built-in print dialog.
 *
 * No external PDF library is required — the browser handles rendering.
 */

import { fetchUnitGenealogy, fetchLotGenealogy } from "../api/runtime";
import type { GenealogyRecord } from "../types";

// ── Helpers ───────────────────────────────────────────────────────

function fmt(dt: string | null | undefined): string {
  if (!dt) return "—";
  return new Date(dt).toLocaleString();
}

function fmtResult(result: string | null | undefined): string {
  if (!result) return "—";
  return result.charAt(0).toUpperCase() + result.slice(1).toLowerCase();
}

function resultColor(result: string | null | undefined): string {
  if (!result) return "#6b7280";
  const r = result.toLowerCase();
  if (r === "pass" || r === "passed") return "#16a34a";
  if (r === "fail" || r === "failed") return "#dc2626";
  if (r === "in_progress") return "#2563eb";
  return "#6b7280";
}

function duration(entered: string | null, exited: string | null): string {
  if (!entered || !exited) return "—";
  const ms = new Date(exited).getTime() - new Date(entered).getTime();
  if (ms < 0) return "—";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

function dataSnapshotRows(snap: Record<string, unknown> | null): string {
  if (!snap || Object.keys(snap).length === 0) return "";
  const rows = Object.entries(snap)
    .map(([k, v]) => `<tr><td style="padding:2px 8px;color:#6b7280;">${k}</td><td style="padding:2px 8px;">${String(v)}</td></tr>`)
    .join("");
  return `
    <table style="margin-top:4px;font-size:11px;border-collapse:collapse;width:100%;">
      ${rows}
    </table>`;
}

// ── HTML builder ──────────────────────────────────────────────────

function buildHtml(rec: GenealogyRecord, title: string, generatedAt: string): string {
  const isUnit = !!rec.unit_id;
  const wipLabel = isUnit ? `Unit — S/N: ${rec.serial_number ?? "—"}` : `Lot — #${rec.lot_number ?? "—"}`;

  // Steps
  const stepsHtml = rec.steps.length === 0
    ? `<tr><td colspan="6" style="text-align:center;color:#9ca3af;padding:8px;">No step history recorded</td></tr>`
    : rec.steps.map((s, i) => {
        const stepLabel = s.step_sequence != null
          ? `${s.step_sequence} — ${s.step_name ?? ""}`
          : (s.step_name ?? "—");
        return `
        <tr style="background:${i % 2 === 0 ? "#ffffff" : "#f9fafb"}">
          <td style="padding:6px 10px;">${stepLabel}</td>
          <td style="padding:6px 10px;">${s.equipment_name ?? "—"}</td>
          <td style="padding:6px 10px;">${fmt(s.entered_at)}</td>
          <td style="padding:6px 10px;">${fmt(s.exited_at)}</td>
          <td style="padding:6px 10px;">${duration(s.entered_at, s.exited_at)}</td>
          <td style="padding:6px 10px;color:${resultColor(s.result)};font-weight:600;">${fmtResult(s.result)}</td>
        </tr>
        ${s.data_snapshot && Object.keys(s.data_snapshot).length ? `
        <tr style="background:#f3f4f6;">
          <td colspan="6" style="padding:2px 10px 6px 32px;">
            ${dataSnapshotRows(s.data_snapshot)}
          </td>
        </tr>` : ""}
      `;
      }).join("");

  // Materials
  const matsHtml = rec.materials.length === 0
    ? `<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:8px;">No materials consumed</td></tr>`
    : rec.materials.map((m, i) => `
        <tr style="background:${i % 2 === 0 ? "#ffffff" : "#f9fafb"};">
          <td style="padding:6px 10px;">${m.material_code ?? "—"}</td>
          <td style="padding:6px 10px;">${m.material_name ?? "—"}</td>
          <td style="padding:6px 10px;">${m.lot_number ?? "—"}</td>
          <td style="padding:6px 10px;">${m.quantity_consumed}</td>
          <td style="padding:6px 10px;">${fmt(m.consumed_at)}</td>
        </tr>
      `).join("");

  // Test results
  const testsHtml = rec.test_results.length === 0
    ? `<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:8px;">No quality tests recorded</td></tr>`
    : rec.test_results.map((t, i) => `
        <tr style="background:${i % 2 === 0 ? "#ffffff" : "#f9fafb"};">
          <td style="padding:6px 10px;">${t.test_code ?? "—"}</td>
          <td style="padding:6px 10px;">${t.test_name ?? "—"}</td>
          <td style="padding:6px 10px;color:${resultColor(t.result)};font-weight:600;">${fmtResult(t.result)}</td>
          <td style="padding:6px 10px;">${fmt(t.tested_at)}</td>
          <td style="padding:6px 10px;">${t.measured_values ? JSON.stringify(t.measured_values) : "—"}</td>
        </tr>
      `).join("");

  // Data points
  const dataHtml = rec.data_points.length === 0
    ? `<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:8px;">No data points collected</td></tr>`
    : rec.data_points.map((d, i) => {
        const val = d.value_numeric != null ? String(d.value_numeric)
          : d.value_string != null ? d.value_string
          : d.value_boolean != null ? (d.value_boolean ? "True" : "False")
          : "—";
        return `
        <tr style="background:${i % 2 === 0 ? "#ffffff" : "#f9fafb"};">
          <td style="padding:6px 10px;">${d.definition_code ?? "—"}</td>
          <td style="padding:6px 10px;">${d.definition_name ?? "—"}</td>
          <td style="padding:6px 10px;">${val}</td>
          <td style="padding:6px 10px;">${fmt(d.collected_at)}</td>
        </tr>`;
      }).join("");

  const thStyle = `style="padding:7px 10px;background:#1e3a5f;color:#fff;text-align:left;font-weight:600;font-size:12px;"`;
  const sectionStyle = `style="margin-top:28px;"`;
  const headingStyle = `style="font-size:14px;font-weight:700;color:#1e3a5f;border-bottom:2px solid #1e3a5f;padding-bottom:4px;margin-bottom:8px;"`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>${title}</title>
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
    .badge { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
    @media print {
      @page { margin: 1.5cm 1.8cm; size: A4; }
      body { padding: 0; font-size: 11px; }
      .no-print { display: none !important; }
      table { page-break-inside: auto; }
      tr { page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <!-- Print button — hidden in print -->
  <div class="no-print" style="text-align:right;margin-bottom:16px;">
    <button onclick="window.print()"
      style="background:#1e3a5f;color:#fff;border:none;border-radius:6px;padding:8px 18px;font-size:13px;cursor:pointer;">
      &#128438; Print / Save as PDF
    </button>
  </div>

  <h1>WIP History Report</h1>
  <p class="subtitle">Generated: ${generatedAt}</p>

  <!-- Summary header -->
  <div class="meta-grid">
    <div class="meta-item"><span class="meta-label">WIP:</span><span class="meta-value">${wipLabel}</span></div>
    <div class="meta-item"><span class="meta-label">Status:</span><span class="meta-value">${rec.status ?? "—"}</span></div>
    <div class="meta-item"><span class="meta-label">Order:</span><span class="meta-value">${rec.order_number ?? rec.order_id ?? "—"}</span></div>
    <div class="meta-item"><span class="meta-label">Product:</span><span class="meta-value">${rec.product_name ?? rec.product_id ?? "—"}</span></div>
  </div>

  <!-- Processing steps -->
  <div ${sectionStyle}>
    <h2 ${headingStyle}>Processing History (${rec.steps.length} step${rec.steps.length !== 1 ? "s" : ""})</h2>
    <table>
      <thead><tr>
        <th ${thStyle}>Step</th>
        <th ${thStyle}>Equipment</th>
        <th ${thStyle}>Started</th>
        <th ${thStyle}>Completed</th>
        <th ${thStyle}>Duration</th>
        <th ${thStyle}>Result</th>
      </tr></thead>
      <tbody>${stepsHtml}</tbody>
    </table>
  </div>

  <!-- Materials consumed -->
  <div ${sectionStyle}>
    <h2 ${headingStyle}>Materials Consumed (${rec.materials.length})</h2>
    <table>
      <thead><tr>
        <th ${thStyle}>Code</th>
        <th ${thStyle}>Name</th>
        <th ${thStyle}>Lot #</th>
        <th ${thStyle}>Qty Consumed</th>
        <th ${thStyle}>Consumed At</th>
      </tr></thead>
      <tbody>${matsHtml}</tbody>
    </table>
  </div>

  <!-- Quality test results -->
  <div ${sectionStyle}>
    <h2 ${headingStyle}>Quality Test Results (${rec.test_results.length})</h2>
    <table>
      <thead><tr>
        <th ${thStyle}>Code</th>
        <th ${thStyle}>Test Name</th>
        <th ${thStyle}>Result</th>
        <th ${thStyle}>Tested At</th>
        <th ${thStyle}>Measured Values</th>
      </tr></thead>
      <tbody>${testsHtml}</tbody>
    </table>
  </div>

  <!-- Data points collected -->
  <div ${sectionStyle}>
    <h2 ${headingStyle}>Data Collected (${rec.data_points.length})</h2>
    <table>
      <thead><tr>
        <th ${thStyle}>Code</th>
        <th ${thStyle}>Definition</th>
        <th ${thStyle}>Value</th>
        <th ${thStyle}>Collected At</th>
      </tr></thead>
      <tbody>${dataHtml}</tbody>
    </table>
  </div>
</body>
</html>`;
}

// ── Public API ────────────────────────────────────────────────────

/**
 * Fetches the genealogy for a unit and opens a printable report in a new window.
 * @param unitId UUID of the unit
 * @param serialNumber Display label for the window title
 */
export async function printUnitHistoryReport(unitId: string, serialNumber: string): Promise<void> {
  const rec = await fetchUnitGenealogy(unitId);
  const generatedAt = new Date().toLocaleString();
  const title = `Unit History — S/N ${serialNumber}`;
  const html = buildHtml(rec, title, generatedAt);
  openPrintWindow(html, title);
}

/**
 * Fetches the genealogy for a lot and opens a printable report in a new window.
 * @param lotId UUID of the lot
 * @param lotNumber Display label for the window title
 */
export async function printLotHistoryReport(lotId: string, lotNumber: string): Promise<void> {
  const rec = await fetchLotGenealogy(lotId);
  const generatedAt = new Date().toLocaleString();
  const title = `Lot History — ${lotNumber}`;
  const html = buildHtml(rec, title, generatedAt);
  openPrintWindow(html, title);
}

function openPrintWindow(html: string, title: string): void {
  const win = window.open("", "_blank", "width=900,height=700,scrollbars=yes");
  if (!win) {
    alert("Pop-up was blocked. Please allow pop-ups for this site and try again.");
    return;
  }
  win.document.open();
  win.document.write(html);
  win.document.close();
  win.document.title = title;
}
