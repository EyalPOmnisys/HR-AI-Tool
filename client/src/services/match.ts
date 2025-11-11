// src/services/match.ts
import type { MatchRunRequest, MatchRunResponse } from '../types/match';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export async function runMatch(payload: MatchRunRequest): Promise<MatchRunResponse> {
  const res = await fetch(`${API_URL}/match/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to run match (${res.status}): ${text}`);
  }
  
  return res.json();
}
