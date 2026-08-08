import type { AssistantPayload } from "../types";

/** Proxied by Vite to FastAPI (see vite.config.ts → :8001). */
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface AskResponse {
  question: string;
  answer: string;
  tool_calls?: { tool: string; arguments: Record<string, unknown> }[];
  tool_results?: unknown[];
  latency_ms?: number;
}

export async function askQuestion(question: string): Promise<AssistantPayload> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  const data = (await res.json()) as AskResponse;
  const tools = (data.tool_calls ?? []).map((c) => c.tool);
  return {
    headline: data.answer || "(empty answer)",
    tools,
    latencyMs: data.latency_ms,
  };
}
