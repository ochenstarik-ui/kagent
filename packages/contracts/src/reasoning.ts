/** Reasoning Engine contracts — capability-first model routing types. */

// ── Capabilities ──────────────────────────

export type Capability =
  | "code_generation"
  | "code_review"
  | "research"
  | "analysis"
  | "planning"
  | "reasoning"
  | "creative"
  | "chat";

export type PrivacyClass = "public" | "internal" | "sensitive" | "restricted";

export type ExecutionMode = "sync" | "stream" | "batch";

export type TaskCategory = "simple" | "standard" | "complex" | "critical";

// ── Requests ─────────────────────────────

export interface ReasoningRequest {
  capability: Capability;
  taskCategory: TaskCategory;
  contextTokens: number;
  toolRequirements: string[];
  privacyClass: PrivacyClass;
  latencyTargetMs: number;
  qualityTarget: number;
  hardBudgetUsd: number;
  executionMode: ExecutionMode;
  metadata: Record<string, unknown>;
}

export interface ExecutionRequest {
  requestId: string;
  messages: Array<{ role: string; content: string }>;
  maxTokens?: number;
  temperature?: number;
}

// ── Model Registry ────────────────────────

export interface ModelInfo {
  id: string;
  provider: string;
  modelName: string;
  capabilities: Capability[];
  pricePer1kInput: number;
  pricePer1kOutput: number;
  maxTokens: number;
  avgLatencyMs: number;
  qualityScore: number;
  privacySupport: PrivacyClass[];
  enabled: boolean;
}

// ── Decisions ────────────────────────────

export interface ModelResult {
  modelId: string;
  provider: string;
  modelName: string;
  estimatedCost: number;
  estimatedLatencyMs: number;
  qualityScore: number;
}

export interface ReasoningDecision {
  requestId: string;
  selected: ModelResult;
  fallbacks: ModelResult[];
  estimatedCost: number;
  confidence: number;
  reasoning: string[];
}

export interface ModelExecution {
  success: boolean;
  modelId: string;
  provider: string;
  tokensInput: number;
  tokensOutput: number;
  costUsd: number;
  latencyMs: number;
  error?: string;
}

// ── Telemetry ─────────────────────────────

export interface TelemetrySummary {
  totalCalls: number;
  totalCostUsd: number;
  successRate: number;
  recent: ModelExecution[];
}
