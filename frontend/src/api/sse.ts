import { getAccessToken } from "./client";
export interface QueryEvent { event: string; data: Record<string, unknown>; }
export async function streamQuery(question: string, sessionId: string, onEvent: (event: QueryEvent) => void, signal?: AbortSignal): Promise<void> {
  const response = await fetch("/api/v1/query/stream", { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + getAccessToken() }, body: JSON.stringify({ question, session_id: sessionId }), signal });
  if (!response.ok || !response.body) { const payload = await response.json().catch(() => ({})); throw new Error(payload.message || "问答请求失败"); }
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
  while (true) { const { value, done } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); const blocks = buffer.split("\n\n"); buffer = blocks.pop() || ""; for (const block of blocks) { let eventName = "message"; let dataText = ""; for (const line of block.split("\n")) { if (line.startsWith("event:")) eventName = line.slice(6).trim(); if (line.startsWith("data:")) dataText += line.slice(5).trim(); } if (dataText) onEvent({ event: eventName, data: JSON.parse(dataText) as Record<string, unknown> }); } }
}
