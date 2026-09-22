/**
 * Typed client for the IncidentIQ backend. Mirrors backend/app/schemas.py —
 * keep these in sync manually for M1/M2 (see docs/architecture.md).
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ImpactLevel = "low" | "medium" | "high" | "critical";
export type UrgencyLevel = "low" | "medium" | "high" | "critical";

export interface IncidentCreate {
  title: string;
  description: string;
  impact?: ImpactLevel | null;
  urgency?: UrgencyLevel | null;
}

export interface PredictionInfo {
  category: string;
  model_name: string;
  model_version: string;
  top_score: number;
  margin_to_second: number;
  confidence_status: "uncalibrated";
  requires_human_review: boolean;
  review_reason: string | null;
}

export interface PriorityInfo {
  priority: string; // "P1".."P4" or "undetermined"
  policy_version: string;
  basis: string;
}

// Mirrors ml/src/incidentiq_ml/config.py CATEGORIES — keep in sync manually.
export const CATEGORIES = [
  "authentication_access",
  "database_data_integrity",
  "api_backend_error",
  "ui_frontend",
  "performance_latency",
  "infrastructure_deployment",
  "third_party_integration",
  "security_vulnerability",
] as const;

// Mirrors backend/app/priority_policy.py VALID_PRIORITY_VALUES.
export const PRIORITY_VALUES = ["P1", "P2", "P3", "P4", "undetermined"] as const;

export interface FeedbackCreate {
  reviewer_name?: string | null;
  corrected_category?: string | null;
  corrected_priority?: string | null;
  note?: string | null;
}

export interface FeedbackResponse {
  id: string;
  incident_id: string;
  created_at: string;
  reviewer_name: string | null;
  corrected_category: string | null;
  corrected_priority: string | null;
  note: string | null;
}

export interface IncidentResponse {
  id: string;
  created_at: string;
  title: string;
  description: string;
  impact: ImpactLevel | null;
  urgency: UrgencyLevel | null;
  prediction: PredictionInfo;
  priority: PriorityInfo;
  reviewed: boolean;
  reviewer_note: string | null;
  feedback: FeedbackResponse[];
}

export type ReviewStatusFilter = "all" | "pending_review" | "reviewed";

export interface IncidentListResponse {
  items: IncidentResponse[];
  total: number;
  limit: number;
  offset: number;
  review_status: ReviewStatusFilter;
}

export interface ReadinessResponse {
  ready: boolean;
  model_loaded: boolean;
  model_error: string | null;
  model_name: string | null;
  model_version: string | null;
  dataset_is_synthetic: boolean | null;
  result_stage: string | null;
}

export interface ApiErrorBody {
  error_code?: string;
  detail?: string | { msg: string }[] | string;
}

export class ApiError extends Error {
  status: number;
  errorCode?: string;

  constructor(status: number, message: string, errorCode?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Could not reach the IncidentIQ backend. Is it running?");
  }

  if (!res.ok) {
    let body: ApiErrorBody = {};
    try {
      body = await res.json();
    } catch {
      // non-JSON error body, fall through with a generic message
    }
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : `Request failed with status ${res.status}`;
    throw new ApiError(res.status, message, body.error_code);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function createIncident(payload: IncidentCreate): Promise<IncidentResponse> {
  return request<IncidentResponse>("/api/v1/incidents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listIncidents(
  limit = 20,
  offset = 0,
  reviewStatus: ReviewStatusFilter = "all",
): Promise<IncidentListResponse> {
  return request<IncidentListResponse>(
    `/api/v1/incidents?limit=${limit}&offset=${offset}&review_status=${reviewStatus}`,
  );
}

export function getIncident(id: string): Promise<IncidentResponse> {
  return request<IncidentResponse>(`/api/v1/incidents/${encodeURIComponent(id)}`);
}

export function getReadiness(): Promise<ReadinessResponse> {
  return request<ReadinessResponse>("/ready");
}

export function submitFeedback(
  incidentId: string,
  payload: FeedbackCreate,
): Promise<FeedbackResponse> {
  return request<FeedbackResponse>(
    `/api/v1/incidents/${encodeURIComponent(incidentId)}/feedback`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}
