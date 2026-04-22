/**
 * Extract a human-readable error message from an axios error coming back
 * from the MES server.
 *
 * Handles the shapes the FastAPI server can return:
 *   - { detail: "string" }                            (HTTPException with str)
 *   - { detail: { errors: ["..."] } }                 (422 validate_parameters)
 *   - { detail: [{ loc, msg, type }, ...] }           (Pydantic 422)
 *   - { error: { message: "..." , details?: {...} } } (MESException / error_response)
 */
export function formatApiError(err: unknown, fallback = "Request failed"): string {
  if (!err) return fallback;

  // axios error shape
  const anyErr = err as {
    response?: { data?: unknown; status?: number };
    message?: string;
  };
  const data = anyErr.response?.data as Record<string, unknown> | undefined;

  if (data && typeof data === "object") {
    // MESException / error_response wrapper
    const wrapped = data.error as { message?: string; details?: unknown } | undefined;
    if (wrapped?.message) return wrapped.message;

    const detail = data.detail;
    if (typeof detail === "string") return detail;

    // 422 from our plugin enable route: { detail: { errors: [...] } }
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const errors = (detail as { errors?: unknown }).errors;
      if (Array.isArray(errors) && errors.length > 0) {
        return errors.map(String).join("; ");
      }
      const msg = (detail as { message?: string }).message;
      if (typeof msg === "string") return msg;
    }

    // Pydantic validation errors: [{ loc, msg, type }, ...]
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) => {
          if (typeof d === "string") return d;
          if (d && typeof d === "object") {
            const loc = Array.isArray((d as { loc?: unknown }).loc)
              ? ((d as { loc: unknown[] }).loc.join(".") as string)
              : "";
            const msg = (d as { msg?: string }).msg ?? "";
            return loc ? `${loc}: ${msg}` : msg;
          }
          return "";
        })
        .filter(Boolean);
      if (msgs.length) return msgs.join("; ");
    }
  }

  if (anyErr.message) return anyErr.message;
  return fallback;
}
