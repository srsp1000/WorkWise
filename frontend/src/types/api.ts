export interface LocationInfo {
  lat: number;
  lon: number;
  city: string;
  state: string;
}

export interface CurrentWeather {
  temperature: number;
  feels_like?: number;
  humidity: number;
  wind_speed: number;
  wind_direction: number;
  weather_code: number;
  description: string;
  uv_index?: number;
  aqi?: number;
  hourly_temps?: number[];
  attribution?: string;
}

export interface CityItem {
  name: string;
  state: string;
  lat: number;
  lon: number;
}

export type TaskIntensity = 'light' | 'moderate' | 'heavy' | 'very_heavy';
export type WorkabilityState = 'GO' | 'EASE' | 'LIMIT' | 'STOP' | 'DATA_UNAVAILABLE';

export interface TaskCatalogItem {
  id: string;
  label: string;
  intensity: TaskIntensity;
  default_duration_h: number;
  outdoor: boolean;
  continuous: boolean;
  dust_generating: boolean;
  depends_on: string[];
  crew_required: number;
  equipment_wind_limit_kmh?: number;
  rain_sensitive?: boolean;
  source_reference?: string;
}

export interface WorkabilityTierMeta {
  id: string;
  label: string;
  description: string;
  intensity: TaskIntensity;
  outdoor: boolean;
}

export interface TasksCatalogResponse {
  tasks: Record<string, TaskCatalogItem>;
  workability_tiers?: WorkabilityTierMeta[];
  grap_stages: Record<number, string>;
  version?: string;
}

export interface TaskHourCell {
  time: string;
  task_id: string;
  task: string;
  intensity: TaskIntensity;
  outdoor: boolean;
  wbgt_c: number | null;
  effective_wbgt_c?: number | null;
  wbgt_method: string;
  limit_c: number;
  margin_c: number | null;
  state: WorkabilityState;
  work_rest: string;
  gates: string[];
  why: string[];
  assumptions?: string[];
}

export interface WorkabilityHeatmapRow {
  tier_id: string;
  tier_label: string;
  description: string;
  intensity: string;
  outdoor: boolean;
  cells: TaskHourCell[];
}

export interface HourlyMatrixRow {
  time: string;
  tasks: Record<string, TaskHourCell>;
}

export interface ScheduledTaskItem {
  task_id: string;
  task: string;
  status: 'SCHEDULED' | 'UNSCHEDULABLE';
  start?: string;
  end?: string;
  continuous?: boolean;
  is_split?: boolean;
  cost?: number;
  crew_required?: number;
  worst_state?: WorkabilityState;
  why_scheduled?: string;
  why_unschedulable?: string;
  recommended_action?: string;
}

export interface PrioritizedAction {
  id: string;
  title: string;
  action: string;
  affected: string;
  why: string;
  constraint: string;
  alternative: string;
  can_apply?: boolean;
  apply_payload?: any;
}

export interface PlanMetadata {
  plan_id: string;
  generated_at: string;
  engine_version: string;
  data_source: string;
  is_simulated: boolean;
  attribution: string;
  data_freshness: string;
  scientific_basis?: string;
}

export interface PlanInputAssumptions {
  site: string;
  lat: number;
  lon: number;
  date: string;
  shift_window: string;
  total_crew_size: number;
  new_crew: boolean;
  grap_stage: number;
  grap_description: string;
  max_concurrent_tasks: number;
}

export interface RestRecommendations {
  heat_protocol_window?: string;
  work_rest_cycle: string;
  hydration_guideline: string;
  shade_requirement: string;
}

export interface PlanResponse {
  site?: string;
  scenario_id?: string;
  date?: string;
  grap_stage: number;
  grap_description: string;
  new_crew: boolean;
  total_crew_size: number;
  workability_heatmap: WorkabilityHeatmapRow[];
  matrix: HourlyMatrixRow[];
  schedule: ScheduledTaskItem[];
  top_recommendation: string;
  prioritized_actions: PrioritizedAction[];
  plan_summary: string;
  metadata?: PlanMetadata;
  input_assumptions?: PlanInputAssumptions;
  rest_recommendations?: RestRecommendations;
  limitations_disclaimer?: string;
}

export interface ScenarioItem {
  id: string;
  title: string;
  description: string;
  default_grap_stage: number;
}

export interface TaskItemInput {
  id: string;
  duration_h?: number;
  intensity?: TaskIntensity;
  continuous?: boolean;
  completed_prior?: boolean;
  depends_on?: string[];
  crew_required?: number;
  equipment_wind_limit_kmh?: number;
  rain_sensitive?: boolean;
}

export interface PlanRequestPayload {
  lat: number;
  lon: number;
  date_str?: string;
  new_crew: boolean;
  grap_stage: number;
  shift_start_hour: number;
  shift_end_hour: number;
  total_crew_size: number;
  max_concurrent_tasks: number;
  tasks: TaskItemInput[];
}
