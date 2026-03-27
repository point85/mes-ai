import { useEffect, useState } from "react";
import {
  syncMaterials,
  createMaterial,
  updateMaterial,
  deleteMaterial,
  getSimulatorOptions,
  type MaterialDefinition,
  type MaterialTypeOption,
  type UOMOption,
} from "../api/erp";

/* ── Blank row template ──────────────────────────────────────────── */

function emptyRow(): MaterialDefinition {
  return {
    code: "",
    name: "",
    material_type: "ROH",
    uom: "EA",
    description: "",
    shelf_life_days: null,
    metadata: {},
  };
}

/* ── Component ───────────────────────────────────────────────────── */

export default function MaterialsPage() {
  const [data, setData] = useState<MaterialDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null); // code being saved

  // Inline editing state
  const [editCode, setEditCode] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<MaterialDefinition | null>(null);

  // Adding new row
  const [adding, setAdding] = useState(false);
  const [newRow, setNewRow] = useState<MaterialDefinition>(emptyRow);

  // Dropdown options
  const [materialTypes, setMaterialTypes] = useState<MaterialTypeOption[]>([]);
  const [uomOptions, setUomOptions] = useState<UOMOption[]>([]);

  /* ── Load options on mount ────────────────────────────────────── */

  useEffect(() => {
    getSimulatorOptions()
      .then((opts) => {
        setMaterialTypes(opts.material_types);
        setUomOptions(opts.uom_options);
      })
      .catch(() => {});
  }, []);

  /* ── Sync ─────────────────────────────────────────────────────── */

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    setEditCode(null);
    setAdding(false);
    try {
      setData(await syncMaterials());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setLoading(false);
    }
  };

  /* ── Create ────────────────────────────────────────────────────── */

  const handleCreate = async () => {
    if (!newRow.code.trim() || !newRow.name.trim()) return;
    setSaving("__new__");
    setError(null);
    try {
      const created = await createMaterial({
        code: newRow.code.trim(),
        name: newRow.name.trim(),
        material_type: newRow.material_type,
        uom: newRow.uom,
        description: newRow.description,
        shelf_life_days: newRow.shelf_life_days,
      });
      setData((prev) => [...prev, created]);
      setNewRow(emptyRow());
      setAdding(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setSaving(null);
    }
  };

  /* ── Update ────────────────────────────────────────────────────── */

  const handleUpdate = async () => {
    if (!editDraft || !editCode) return;
    setSaving(editCode);
    setError(null);
    try {
      const updated = await updateMaterial(editCode, {
        name: editDraft.name,
        material_type: editDraft.material_type,
        uom: editDraft.uom,
        description: editDraft.description,
        shelf_life_days: editDraft.shelf_life_days,
      });
      setData((prev) => prev.map((m) => (m.code === editCode ? updated : m)));
      setEditCode(null);
      setEditDraft(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(null);
    }
  };

  /* ── Delete ────────────────────────────────────────────────────── */

  const handleDelete = async (code: string) => {
    setSaving(code);
    setError(null);
    try {
      await deleteMaterial(code);
      setData((prev) => prev.filter((m) => m.code !== code));
      if (editCode === code) {
        setEditCode(null);
        setEditDraft(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setSaving(null);
    }
  };

  /* ── Start editing ─────────────────────────────────────────────── */

  const startEdit = (row: MaterialDefinition) => {
    setEditCode(row.code);
    setEditDraft({ ...row });
    setAdding(false);
  };

  const cancelEdit = () => {
    setEditCode(null);
    setEditDraft(null);
  };

  /* ── Shared cell classes ────────────────────────────────────────── */

  const inputCls =
    "w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400";
  const selectCls =
    "w-full px-2 py-1 text-sm border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-blue-400";
  const btnCls =
    "px-2 py-1 text-xs rounded disabled:opacity-40";

  /* ── Render ────────────────────────────────────────────────────── */

  return (
    <div className="space-y-4">
      {/* Action bar */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSync}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Syncing…" : "Sync Materials"}
        </button>
        {!adding && (
          <button
            onClick={() => { setAdding(true); setEditCode(null); }}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700"
          >
            + Add Material
          </button>
        )}
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} materials</span>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}

      {/* Table */}
      <div className="overflow-x-auto bg-white rounded-lg border">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["Code", "Name", "SAP Type", "UoM", "Description", "Shelf Life", "Actions"].map(
                (h) => (
                  <th
                    key={h}
                    className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {/* ── Add-new row ─────────────────────────────────── */}
            {adding && (
              <tr className="bg-green-50">
                <td className="px-3 py-2">
                  <input
                    className={inputCls}
                    placeholder="Code"
                    value={newRow.code}
                    onChange={(e) => setNewRow({ ...newRow, code: e.target.value })}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    className={inputCls}
                    placeholder="Name"
                    value={newRow.name}
                    onChange={(e) => setNewRow({ ...newRow, name: e.target.value })}
                  />
                </td>
                <td className="px-3 py-2">
                  <select
                    className={selectCls}
                    value={newRow.material_type}
                    onChange={(e) => setNewRow({ ...newRow, material_type: e.target.value })}
                  >
                    {materialTypes.map((t) => (
                      <option key={t.code} value={t.code}>
                        {t.code} — {t.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <select
                    className={selectCls}
                    value={newRow.uom}
                    onChange={(e) => setNewRow({ ...newRow, uom: e.target.value })}
                  >
                    {uomOptions.map((u) => (
                      <option key={u.symbol} value={u.symbol}>
                        {u.symbol} — {u.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input
                    className={inputCls}
                    placeholder="Description"
                    value={newRow.description}
                    onChange={(e) => setNewRow({ ...newRow, description: e.target.value })}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    className={inputCls}
                    type="number"
                    placeholder="Days"
                    value={newRow.shelf_life_days ?? ""}
                    onChange={(e) =>
                      setNewRow({
                        ...newRow,
                        shelf_life_days: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                  />
                </td>
                <td className="px-3 py-2 whitespace-nowrap space-x-1">
                  <button
                    className={`${btnCls} bg-green-600 text-white hover:bg-green-700`}
                    disabled={saving === "__new__" || !newRow.code.trim() || !newRow.name.trim()}
                    onClick={handleCreate}
                  >
                    {saving === "__new__" ? "Saving…" : "Save"}
                  </button>
                  <button
                    className={`${btnCls} bg-gray-300 text-gray-700 hover:bg-gray-400`}
                    onClick={() => { setAdding(false); setNewRow(emptyRow()); }}
                  >
                    Cancel
                  </button>
                </td>
              </tr>
            )}

            {/* ── Data rows ───────────────────────────────────── */}
            {data.length === 0 && !adding ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-500">
                  Click &apos;Sync Materials&apos; to pull material master from SAP
                </td>
              </tr>
            ) : (
              data.map((row) => {
                const isEditing = editCode === row.code;
                const draft = isEditing && editDraft ? editDraft : row;
                const busy = saving === row.code;

                return (
                  <tr key={row.code} className={isEditing ? "bg-blue-50" : "hover:bg-gray-50"}>
                    {/* Code — not editable */}
                    <td className="px-3 py-2 font-mono whitespace-nowrap">{row.code}</td>

                    {/* Name */}
                    <td className="px-3 py-2">
                      {isEditing ? (
                        <input
                          className={inputCls}
                          value={draft.name}
                          onChange={(e) => setEditDraft({ ...draft, name: e.target.value })}
                        />
                      ) : (
                        row.name
                      )}
                    </td>

                    {/* SAP Type dropdown */}
                    <td className="px-3 py-2">
                      {isEditing ? (
                        <select
                          className={selectCls}
                          value={String(draft.metadata?.sap_material_type ?? draft.material_type)}
                          onChange={(e) => setEditDraft({ ...draft, material_type: e.target.value })}
                        >
                          {materialTypes.map((t) => (
                            <option key={t.code} value={t.code}>
                              {t.code} — {t.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        String(row.metadata?.sap_material_type ?? row.material_type)
                      )}
                    </td>

                    {/* UoM dropdown */}
                    <td className="px-3 py-2">
                      {isEditing ? (
                        <select
                          className={selectCls}
                          value={draft.uom}
                          onChange={(e) => setEditDraft({ ...draft, uom: e.target.value })}
                        >
                          {uomOptions.map((u) => (
                            <option key={u.symbol} value={u.symbol}>
                              {u.symbol} — {u.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        row.uom
                      )}
                    </td>

                    {/* Description */}
                    <td className="px-3 py-2">
                      {isEditing ? (
                        <input
                          className={inputCls}
                          value={draft.description}
                          onChange={(e) => setEditDraft({ ...draft, description: e.target.value })}
                        />
                      ) : (
                        row.description
                      )}
                    </td>

                    {/* Shelf life */}
                    <td className="px-3 py-2">
                      {isEditing ? (
                        <input
                          className={inputCls}
                          type="number"
                          value={draft.shelf_life_days ?? ""}
                          onChange={(e) =>
                            setEditDraft({
                              ...draft,
                              shelf_life_days: e.target.value ? Number(e.target.value) : null,
                            })
                          }
                        />
                      ) : (
                        row.shelf_life_days != null ? String(row.shelf_life_days) : "—"
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-3 py-2 whitespace-nowrap space-x-1">
                      {isEditing ? (
                        <>
                          <button
                            className={`${btnCls} bg-blue-600 text-white hover:bg-blue-700`}
                            disabled={busy}
                            onClick={handleUpdate}
                          >
                            {busy ? "Saving…" : "Save"}
                          </button>
                          <button
                            className={`${btnCls} bg-gray-300 text-gray-700 hover:bg-gray-400`}
                            onClick={cancelEdit}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className={`${btnCls} bg-blue-100 text-blue-700 hover:bg-blue-200`}
                            onClick={() => startEdit(row)}
                          >
                            Edit
                          </button>
                          <button
                            className={`${btnCls} bg-red-100 text-red-700 hover:bg-red-200`}
                            disabled={busy}
                            onClick={() => handleDelete(row.code)}
                          >
                            {busy ? "…" : "Delete"}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
