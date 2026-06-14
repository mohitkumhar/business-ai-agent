export interface CompletedNode {
  name: string;
  friendlyName: string;
}

export type AgentStatus =
  | { kind: "idle" }
  | { kind: "connecting" }
  | { kind: "streaming"; label: string; node?: string }
  | { kind: "clarification"; text: string };

export type SyncStatus =
  | { kind: "loading"; label: string }
  | { kind: "syncing"; label: string }
  | { kind: "synced"; label: string }
  | { kind: "local"; label: string };