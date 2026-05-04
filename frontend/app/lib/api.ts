/**
 * frontend/app/lib/api.ts
 *
 * Shared HTTP + SSE client for the MedVerse backend.
 *
 * - Base URL from `NEXT_PUBLIC_API_URL` (default http://localhost:8000
 *   so dev-server usage keeps working without a .env file).
 * - Transparent bearer-token injection from localStorage.medverse_token.
 * - Typed helpers for GET / POST / POST-FormData.
 * - SSE URL builder that attaches the token as a query param because
 *   EventSource can't carry custom headers.
 */

export const API_URL =
  (typeof process !== "undefined" && process.env && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export const TOKEN_STORAGE_KEY = "medverse_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    // Mirror to a cookie so server-side middleware can gate routes.
    document.cookie = `${TOKEN_STORAGE_KEY}=${token}; Path=/; Max-Age=${60 * 60 * 8}; SameSite=Lax`;
  } catch {
    /* noop */
  }
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    document.cookie = `${TOKEN_STORAGE_KEY}=; Path=/; Max-Age=0`;
  } catch {
    /* noop */
  }
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

function handle401(): void {
  if (typeof window === "undefined") return;
  clearToken();
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

export async function apiGet<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(init.headers || {}), ...authHeaders() },
  });
  if (res.status === 401) {
    handle401();
    throw new Error(`GET ${path} → 401`);
  }
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (res.status === 401) {
    handle401();
    throw new Error(`POST ${path} → 401`);
  }
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (res.status === 401) {
    handle401();
    throw new Error(`PATCH ${path} → 401`);
  }
  if (!res.ok) throw new Error(`PATCH ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: form,
  });
  if (res.status === 401) {
    handle401();
    throw new Error(`POST ${path} → 401`);
  }
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

/**
 * Build the EventSource URL for /stream. EventSource can't attach
 * Authorization headers, so when a token is present we append it as a
 * query parameter — the backend's /stream handler honors ?token=.
 */
export function buildStreamUrl(path = "/stream", extra: Record<string, string> = {}): string {
  const url = new URL(`${API_URL}${path}`);
  const token = getToken();
  if (token) url.searchParams.set("token", token);
  for (const [k, v] of Object.entries(extra)) {
    if (v) url.searchParams.set(k, v);
  }
  return url.toString();
}

// ─── Auth helpers ─────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  auth_enabled: boolean;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await apiPost<LoginResponse>("/api/auth/login", { username, password });
  if (res?.access_token) setToken(res.access_token);
  return res;
}

export async function logout(): Promise<void> {
  clearToken();
}

// ─── History series (for /history page) ───────────────────────────

export interface HistoryPoint {
  ts: string;
  hr: number | null;
  spo2: number | null;
  br: number | null;
  hrv: number | null;
}

export function fetchHistory(
  params: { resolution?: "1m" | "1h"; patient_id?: string; limit?: number } = {}
): Promise<HistoryPoint[]> {
  const qs = new URLSearchParams();
  if (params.resolution) qs.set("resolution", params.resolution);
  if (params.patient_id) qs.set("patient_id", params.patient_id);
  if (params.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiGet<HistoryPoint[]>(`/api/history${q ? `?${q}` : ""}`);
}

// ─── Backend status ───────────────────────────────────────────────

export interface BackendStatus {
  vest_connected: boolean;
  fetal_connected: boolean;
  using_mock: boolean;
  vest_device: string;
  fetal_device: string;
  sample_rate: number;
  buffer_size: number;
  packets_received: number;
}

export function getStatus(): Promise<BackendStatus> {
  return apiGet<BackendStatus>("/api/status");
}

// ─── Interpretations (per-specialty agent output) ─────────────────

export interface Interpretation {
  interpretation: string;
  severity: string;
  severity_score: number;
  generated_at: string;
}

export type InterpretationsMap = Record<string, Interpretation>;

export function fetchInterpretations(patient_id?: string): Promise<InterpretationsMap> {
  const q = patient_id ? `?patient_id=${encodeURIComponent(patient_id)}` : "";
  return apiGet<InterpretationsMap>(`/api/interpretations${q}`);
}

// ─── Snapshot ─────────────────────────────────────────────────────

export function getSnapshot(patient_id?: string): Promise<unknown> {
  const q = patient_id ? `?patient_id=${encodeURIComponent(patient_id)}` : "";
  return apiGet<unknown>(`/api/snapshot${q}`);
}

// ─── Simulation ───────────────────────────────────────────────────

export type Scenario = "normal" | "tachycardia" | "hypoxia" | "fetal_decel" | "arrhythmia";

export function getScenario(): Promise<{ scenario: Scenario; available: Scenario[] }> {
  return apiGet("/api/simulation/scenario");
}

export function setScenario(scenario: Scenario) {
  return apiPost<{ status: string; scenario: Scenario }>("/api/simulation/scenario", { scenario });
}

export function setSimulationMode(mode: string) {
  return apiPost<{ status: string; mode: string }>("/api/simulation/mode", { mode });
}

export function injectMedication(medication: string, dose: number) {
  return apiPost<{ status: string; medication: string; dose: number }>("/api/simulation/medicate", {
    medication,
    dose,
  });
}

export function setCYP2D6(status: "Normal Metabolizer" | "Poor Metabolizer") {
  return apiPost<{ status: string; cyp2d6_status: string }>("/api/simulation/cyp2d6", { status });
}

// ─── Patients (Phase 3) ───────────────────────────────────────────

export interface Patient {
  id: string;
  mrn: string | null;
  name: string;
  dob: string | null;
  sex: string | null;
  gestational_age_weeks: number | null;
  conditions: string[];
  assigned_clinician_id: string | null;
  created_at: string;
}

export function listPatients(): Promise<Patient[]> {
  return apiGet<Patient[]>("/api/patients");
}

export function getPatient(id: string): Promise<Patient> {
  return apiGet<Patient>(`/api/patients/${encodeURIComponent(id)}`);
}

export function createPatient(p: Partial<Patient> & { name: string }): Promise<Patient> {
  return apiPost<Patient>("/api/patients", p);
}

export function updatePatient(id: string, p: Partial<Patient>): Promise<Patient> {
  return apiPatch<Patient>(`/api/patients/${encodeURIComponent(id)}`, p);
}

// ─── Alerts (Phase 4) ─────────────────────────────────────────────

export interface Alert {
  id: number;
  patient_id: string;
  severity: number;
  source: string;
  message: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export function fetchAlerts(params: { patient_id?: string; unacknowledged?: boolean; limit?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.patient_id) qs.set("patient_id", params.patient_id);
  if (params.unacknowledged) qs.set("unacknowledged", "true");
  if (params.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiGet<Alert[]>(`/api/alerts${q ? `?${q}` : ""}`);
}

export function acknowledgeAlert(id: number, note?: string) {
  return apiPost<{ status: string }>(`/api/alerts/${id}/acknowledge`, { note: note || "" });
}

export function buildAlertsStreamUrl(patient_id?: string): string {
  return buildStreamUrl("/api/alerts/stream", patient_id ? { patient_id } : {});
}

// ─── Agent invocation (Phase 5) ───────────────────────────────────

export interface AgentResponse {
  reply: string;
  severity: string;
  severity_score: number;
  specialty: string;
}

export function askAgent(specialty: string, message: string, patient_id?: string) {
  return apiPost<AgentResponse>("/api/agent/ask", { specialty, message, patient_id });
}

export function runAgentNow(patient_id?: string, specialty?: string) {
  const qs = new URLSearchParams();
  if (patient_id) qs.set("patient_id", patient_id);
  if (specialty) qs.set("specialty", specialty);
  return apiPost<{ status: string; ran: string[] }>(`/api/agent/run-now?${qs}`, {});
}

// ─── Collaborative diagnosis (Phase 1 of agentic upgrade) ─────────

export interface CandidateEvidence {
  source: string;
  verdict: "supports" | "contradicts" | "neutral";
  feature: string;
  weight: number;
  note: string;
}

export interface CandidateDiagnosis {
  name: string;
  icd10?: string | null;
  rarity: "common" | "uncommon" | "rare";
  score: number;
  evidence: CandidateEvidence[];
  recommended_tests?: string[];
}

export interface ReasoningStep {
  ts: string;
  node: string;
  kind: "analyser" | "llm" | "planner" | "rag" | "verdict";
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  confidence: number;
  supports: string[];
  contradicts: string[];
  note: string;
}

export interface ComplexDiagnosisResponse {
  status: string;
  patient_id: string;
  selected_specialties: string[];
  planner_rationale: string;
  candidates: CandidateDiagnosis[];
  final_ranking: CandidateDiagnosis[];
  recommended_next_tests: string[];
  summary_for_clinician: string;
  traces: ReasoningStep[];
  error?: string;
}

export function runComplexDiagnosis(patient_id?: string) {
  const qs = new URLSearchParams();
  if (patient_id) qs.set("patient_id", patient_id);
  return apiPost<ComplexDiagnosisResponse>(`/api/agent/complex-diagnosis?${qs}`, {});
}

// ─── Image upload (Phase 2.A: feeds retina / skin runtime adapters) ─

export interface UploadImageResponse {
  status: string;
  patient_id?: string;
  modality?: string;
  image_path?: string;
  filename?: string;
  size_bytes?: number;
  error?: string;
}

export async function uploadImage(
  file: File,
  modality: "retinal" | "skin",
  patient_id?: string,
): Promise<UploadImageResponse> {
  const form = new FormData();
  form.append("file", file);
  const qs = new URLSearchParams({ modality });
  if (patient_id) qs.set("patient_id", patient_id);
  return apiPostForm<UploadImageResponse>(`/api/upload-image?${qs}`, form);
}

// ─── Digital twin (Phase 3 of agentic upgrade) ───────────────────

export type TwinName = "cardiac" | "maternal_fetal";

export interface TwinTreatmentStep {
  t_min: number;
  drug: string;
  dose_mg: number;
}

export interface TwinTrajectoryPoint {
  t_s: number;
  state: Record<string, unknown>;
}

export interface TwinSimulationResponse {
  status: string;
  run_id?: string;
  twin: TwinName;
  patient_id: string;
  horizon_min: number;
  trajectory: TwinTrajectoryPoint[];
  error?: string;
}

export interface TwinTimelineResponse {
  status: string;
  twin: TwinName;
  patient_id: string;
  count: number;
  states: { ts: number; state: Record<string, unknown> }[];
  error?: string;
}

export interface TwinRunSummary {
  id: string;
  ts: string;
  twin: TwinName;
  kind: "scenario" | "plan" | "replay";
  horizon_min: number;
}

export function runTwinScenario(
  body: {
    twin: TwinName;
    patient_id?: string;
    inputs?: Record<string, unknown>;
    horizon_min?: number;
    step_s?: number;
  },
): Promise<TwinSimulationResponse> {
  return apiPost<TwinSimulationResponse>("/api/digital-twin/scenario", body);
}

export function runTwinPlan(
  body: {
    twin: TwinName;
    patient_id?: string;
    inputs?: Record<string, unknown>;
    treatment_steps: TwinTreatmentStep[];
    horizon_min?: number;
    step_s?: number;
  },
): Promise<TwinSimulationResponse> {
  return apiPost<TwinSimulationResponse>("/api/digital-twin/plan", body);
}

export function fetchTwinTimeline(
  twin: TwinName,
  opts: { patient_id?: string; from_ts?: number; to_ts?: number; limit?: number } = {},
): Promise<TwinTimelineResponse> {
  const qs = new URLSearchParams({ twin });
  if (opts.patient_id) qs.set("patient_id", opts.patient_id);
  if (opts.from_ts !== undefined) qs.set("from_ts", String(opts.from_ts));
  if (opts.to_ts !== undefined) qs.set("to_ts", String(opts.to_ts));
  if (opts.limit !== undefined) qs.set("limit", String(opts.limit));
  return apiGet<TwinTimelineResponse>(`/api/digital-twin/timeline?${qs}`);
}

export function fetchTwinRuns(
  patient_id?: string,
  limit = 50,
): Promise<{ status: string; patient_id: string; runs: TwinRunSummary[] }> {
  const qs = new URLSearchParams();
  if (patient_id) qs.set("patient_id", patient_id);
  qs.set("limit", String(limit));
  return apiGet(`/api/digital-twin/runs?${qs}`);
}

// ─── Care plans (Phase 6) ─────────────────────────────────────────

export interface CarePlan {
  id: string;
  name: string;
  conditions: string[];
  thresholds: Record<string, { min?: number; max?: number; severity: number }>;
  monitoring_frequency_s: number;
}

export function listCarePlans(): Promise<CarePlan[]> {
  return apiGet<CarePlan[]>("/api/care-plans");
}

export function assignCarePlan(patient_id: string, care_plan_id: string) {
  return apiPost<{ status: string }>(`/api/patients/${encodeURIComponent(patient_id)}/care-plan`, {
    care_plan_id,
  });
}

// ─── FHIR (Phase 7) ───────────────────────────────────────────────

export const FHIR_RESOURCES = [
  { key: "observation", path: "/api/fhir/Observation/latest", label: "Observation (latest)" },
  { key: "bundle", path: "/api/fhir/Bundle/latest", label: "Bundle (latest)" },
  { key: "diag-all", path: "/api/fhir/DiagnosticReport/latest", label: "DiagnosticReport (all specialties)" },
  { key: "device", path: "/api/fhir/Device", label: "Device" },
] as const;

export function fetchFhir<T = unknown>(path: string, patient_id?: string): Promise<T> {
  const q = patient_id ? `?patient_id=${encodeURIComponent(patient_id)}` : "";
  return apiGet<T>(`${path}${q}`);
}

// ─── Auth verification (Phase 8) ──────────────────────────────────

export interface AuthMe {
  user: { sub: string; anonymous?: boolean };
  auth_enabled: boolean;
}

export function getMe(): Promise<AuthMe> {
  return apiGet<AuthMe>("/api/auth/me");
}

// ─── Emergency (Phase 12) ─────────────────────────────────────────

export function postEmergency(payload: {
  patient_id?: string;
  message: string;
  vitals: Record<string, unknown>;
  geolocation?: { lat: number; lon: number };
}) {
  return apiPost<{ status: string; webhook?: string }>("/api/emergency", payload);
}
