import type {
  PlanRequestPayload,
  PlanResponse,
  ScenarioItem,
  TasksCatalogResponse,
  CurrentWeather,
  CityItem
} from '../types/api';

const API_BASE = '/api';

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
