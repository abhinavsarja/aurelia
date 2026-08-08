export type EvidenceKind = "m" | "d" | "x";

export interface EvidenceBlock {
  kind: EvidenceKind;
  tag: string;
  text: string;
  source: string;
}

export interface GapPart {
  label: string;
  pct: string;
  width: number;
  muted?: boolean;
}

export interface AssistantPayload {
  headline: string;
  gaps?: GapPart[];
  evidence?: EvidenceBlock[];
  action?: string;
  plain?: string;
  tools?: string[];
  latencyMs?: number;
}

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; payload: AssistantPayload };
