import type {
  Backtest,
  ShadowModelReport,
  CompleteActionResult,
  EvidenceAnswer,
  EvidenceQuery,
  Health,
  HistoryPoint,
  IndexStatus,
  RankingRow,
  RecordDetail,
  RowError,
  UploadDiff,
  UploadRecord,
  UploadResult,
  VesselAction,
  VesselIssues,
  VesselRisk,
} from "./types";

const KEY_STORAGE = "esm.shiprisk.apiKey";
const USER_STORAGE = "esm.shiprisk.user";

export const session = {
  apiKey: () => localStorage.getItem(KEY_STORAGE) ?? "",
  user: () => localStorage.getItem(USER_STORAGE) ?? "",
  save(apiKey: string, user: string) {
    localStorage.setItem(KEY_STORAGE, apiKey.trim());
    localStorage.setItem(USER_STORAGE, user.trim());
  },
  clear() {
    localStorage.removeItem(KEY_STORAGE);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public rowErrors: RowError[] = [],
  ) {
    super(message);
  }
}

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", session.apiKey());
  if (session.user()) headers.set("X-User", session.user());
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const res = await fetch(path, { ...init, headers });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const rowErrors = (body && Array.isArray(body.errors) ? body.errors : []) as RowError[];
    throw new ApiError(res.status, detailMessage(body, res.statusText), rowErrors);
  }
  return body as T;
}

function query(params: object): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/** Sign the Chainlit assistant in with the dashboard API key so the chat iframe skips its login form. */
export async function signInFleetChat(): Promise<boolean> {
  const password = session.apiKey();
  if (!password) return false;
  const body = new URLSearchParams();
  body.set("username", session.user() || "chat");
  body.set("password", password);
  try {
    const res = await fetch("/chat/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
      credentials: "include",
    });
    return res.ok;
  } catch {
    return false;
  }
}

export const api = {
  health: () => request<Health>("/api/health"),
  ranking: () => request<RankingRow[]>("/api/fleet/ranking"),
  vesselRisk: (id: string) => request<VesselRisk>(`/api/vessels/${id}/risk`),
  vesselHistory: (id: string) => request<HistoryPoint[]>(`/api/vessels/${id}/history`),
  vesselIssues: (id: string) => request<VesselIssues>(`/api/vessels/${id}/issues`),
  vesselActions: (id: string, includeClosed = true) =>
    request<VesselAction[]>(`/api/vessels/${id}/actions${query({ include_closed: includeClosed })}`),
  completeAction: (id: string, actionId: number, evidence: string) =>
    request<CompleteActionResult>(`/api/vessels/${id}/actions/${actionId}/complete`, {
      method: "POST",
      body: JSON.stringify({ evidence }),
    }),
  evidence: (id: string, q: EvidenceQuery) => request<EvidenceAnswer>(`/api/vessels/${id}/evidence${query(q)}`),
  uploads: () => request<UploadRecord[]>("/api/uploads"),
  uploadDiff: (uploadId: number) => request<UploadDiff>(`/api/uploads/${uploadId}/diff`),
  upload: (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));
    return request<UploadResult>("/api/upload", { method: "POST", body: form });
  },
  backtest: (topN: number) => request<Backtest>(`/api/backtest${query({ top_n: topN })}`),
  riskModel: () => request<ShadowModelReport>("/api/risk-model"),
  indexStatus: () => request<IndexStatus>("/api/index/status"),
  record: (id: string) => request<RecordDetail>(`/api/records/${encodeURIComponent(id)}`),
};
