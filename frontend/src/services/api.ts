import type {
  PlanRequestPayload,
  PlanResponse,
  ScenarioItem,
  TasksCatalogResponse,
  CurrentWeather,
  CityItem
} from '../types/api';

const LIVE_API_URL = 'https://ur0qwu5k8d.execute-api.ap-south-1.amazonaws.com/api';

const isDev = typeof window !== 'undefined' && Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1' ||
  window.location.port === '5180' ||
  window.location.port === '5173'
);

const envBase = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, '');
const defaultBase = isDev ? '/api' : LIVE_API_URL;
const rawBase = envBase || defaultBase;
export const API_BASE = rawBase.endsWith('/api') ? rawBase : `${rawBase}/api`;

export async function fetchTasksCatalog(): Promise<TasksCatalogResponse> {
  const res = await fetch(`${API_BASE}/tasks`);
  if (!res.ok) {
    throw new Error(`Failed to fetch tasks catalog: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchScenariosList(): Promise<ScenarioItem[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) {
    throw new Error(`Failed to fetch scenarios: ${res.statusText}`);
  }
  const data = await res.json();
  return data.scenarios;
}

export async function generateLivePlan(payload: PlanRequestPayload): Promise<PlanResponse> {
  const res = await fetch(`${API_BASE}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Plan generation failed: ${res.statusText}`);
  }
  return res.json();
}

export async function generateScenarioPlan(
  scenarioId: string,
  payload: Omit<PlanRequestPayload, 'date_str'>
): Promise<PlanResponse> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Scenario plan generation failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCities(): Promise<CityItem[]> {
  const res = await fetch(`${API_BASE}/cities`);
  if (!res.ok) throw new Error(`Failed to fetch cities: ${res.statusText}`);
  const data = await res.json();
  return data.cities;
}

export async function fetchCurrentWeather(lat: number, lon: number): Promise<CurrentWeather> {
  const res = await fetch(`${API_BASE}/weather/current?lat=${lat}&lon=${lon}`);
  if (!res.ok) throw new Error(`Failed to fetch current weather: ${res.statusText}`);
  return res.json();
}

export async function reverseGeocode(lat: number, lon: number): Promise<{ city: string; state: string }> {
  const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`);
  if (!res.ok) throw new Error('Reverse geocode failed');
  const data = await res.json();
  const address = data.address || {};
  return {
    city: address.city || address.town || address.village || address.state_district || 'Unknown City',
    state: address.state || 'Unknown State',
  };
}

export interface AudioSynthesisResult {
  status: 'success' | 'fallback';
  provider: string;
  mode: string;
  audio_base64: string | null;
  s3_key?: string | null;
  text: string;
  language: string;
  voice?: string;
  notice?: string;
}

export async function synthesizeAudioBrief(
  text: string,
  language: 'hi-IN' | 'en-IN' = 'hi-IN',
  voiceId?: string
): Promise<AudioSynthesisResult> {
  const res = await fetch(`${API_BASE}/audio/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language, voice_id: voiceId }),
  });
  if (!res.ok) {
    throw new Error(`Audio synthesis request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function askSupervisorAI(payload: { question: string; plan: PlanResponse }) {
  const res = await fetch(`${API_BASE}/ai/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`AI assistant query failed: ${res.statusText}`);
  }
  return res.json();
}
