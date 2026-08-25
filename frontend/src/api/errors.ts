interface ValidationError {
  loc?: Array<string | number>;
  msg?: string;
}

interface ErrorPayload {
  detail?: string | ValidationError[];
}

export async function getApiError(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as ErrorPayload | null;
  const detail = payload?.detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((error) => {
        const field = error.loc?.at(-1);
        return field && error.msg ? `${String(field)}: ${error.msg}` : error.msg;
      })
      .filter(Boolean)
      .join("; ") || "Invalid input";
  }
  return `Request failed (${response.status})`;
}
