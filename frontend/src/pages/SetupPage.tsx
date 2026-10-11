import React from 'react';
import type { TaskCatalogItem, TaskItemInput, ScenarioItem, LocationInfo } from '../types/api';
import { TaskSelector } from '../components/TaskSelector';
import { ScenarioSelector } from '../components/ScenarioSelector';
import { LocationDetector } from '../components/LocationDetector';
import { WeatherDashboard } from '../components/WeatherDashboard';
import { VoiceInput } from '../components/VoiceInput';
import { MapPin, Sparkles } from 'lucide-react';

interface SetupPageProps {
  catalog: Record<string, TaskCatalogItem>;
  grapStages: Record<number, string>;
  scenarios: ScenarioItem[];
  selectedScenarioId: string;
  onSelectScenario: (id: string) => void;
  onSelectLive: () => void;
  location: LocationInfo;
  onLocationChange: (loc: LocationInfo) => void;
  crewSize: number;
  setCrewSize: (size: number) => void;
  newCrew: boolean;
  setNewCrew: (newCrew: boolean) => void;
  grapStage: number;
  setGrapStage: (stage: number) => void;
  shiftStart: number;
  setShiftStart: (h: number) => void;
  shiftEnd: number;
  setShiftEnd: (h: number) => void;
  selectedTasks: TaskItemInput[];
  setSelectedTasks: (tasks: TaskItemInput[]) => void;
  onGeneratePlan: () => void;
  isLoading: boolean;
}

export const SetupPage: React.FC<SetupPageProps> = ({
  catalog,
  grapStages,
  scenarios,
  selectedScenarioId,
  onSelectScenario,
  onSelectLive,
  location,
  onLocationChange,
  crewSize,
  setCrewSize,
  newCrew,
  setNewCrew,
  grapStage,
  setGrapStage,
  shiftStart,
  setShiftStart,
  shiftEnd,
  setShiftEnd,
  selectedTasks,
  setSelectedTasks,
  onGeneratePlan,
  isLoading,
}) => {
  const handleApplyParsedPlan = (parsed: {
    crewSize?: number;
    shiftStart?: number;
    shiftEnd?: number;
    newCrew?: boolean;
    grapStage?: number;
    tasks: TaskItemInput[];
  }) => {
    if (parsed.crewSize !== undefined) setCrewSize(parsed.crewSize);
    if (parsed.shiftStart !== undefined) setShiftStart(parsed.shiftStart);
    if (parsed.shiftEnd !== undefined) setShiftEnd(parsed.shiftEnd);
    if (parsed.newCrew !== undefined) setNewCrew(parsed.newCrew);
    if (parsed.grapStage !== undefined) setGrapStage(parsed.grapStage);
    if (parsed.tasks && parsed.tasks.length > 0) setSelectedTasks(parsed.tasks);
  };

  return (
    <div>
      {/* Secondary Weather Dashboard */}
      <WeatherDashboard lat={location.lat} lon={location.lon} city={location.city} />

      {/* Multimodal Voice & Natural Language Text Input Assistant */}
      <VoiceInput catalog={catalog} onApplyParsedPlan={handleApplyParsedPlan} />

      {/* Site & Crew Parameter Setup */}
      <div className="field-card">
        <div className="field-card-header">
          <div className="field-card-title">
            <MapPin size={20} className="text-blue-700" />
            <span>Site Location & Crew Headcount</span>
          </div>
          <LocationDetector location={location} onLocationChange={onLocationChange} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
          {/* Left: Crew & Acclimatization */}
          <div>
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <label className="form-label" style={{ marginBottom: 0 }}>Total Available Workers</label>
                <span style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--brand-navy)' }}>
                  {crewSize} Workers
                </span>
              </div>
              <input
                type="range"
                min="5"
                max="50"
                value={crewSize}
                onChange={(e) => setCrewSize(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--brand-navy)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                <span>Min: 5</span>
                <span>Default: 18</span>
                <span>Max: 50</span>
              </div>
            </div>

            {/* Acclimatization Toggle */}
            <div
              style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem',
              }}
            >
              <div>
                <span style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                  New / Unacclimatized Crew?
                </span>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Applies strict OSHA / NIOSH RAL limits (-2°C to -4°C baseline reduction)
                </p>
              </div>
              <input
                type="checkbox"
                checked={newCrew}
                onChange={(e) => setNewCrew(e.target.checked)}
                style={{ width: 20, height: 20, accentColor: '#059669', cursor: 'pointer' }}
              />
            </div>
          </div>

          {/* Right: CAQM GRAP Stage & Shift Window */}
          <div>
            <div className="form-group">
              <label className="form-label">CAQM Delhi-NCR GRAP Stage</label>
              <select
                value={grapStage}
                onChange={(e) => setGrapStage(Number(e.target.value))}
                className="form-select"
              >
                {Object.entries(grapStages).map(([stageNum, label]) => (
                  <option key={stageNum} value={stageNum}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Shift Hours (24-Hour Schedule)</label>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Start Hour (IST)</span>
                  <select
                    value={shiftStart}
                    onChange={(e) => setShiftStart(Number(e.target.value))}
                    className="form-select"
                  >
                    {[5, 6, 7, 8, 9].map((h) => (
                      <option key={h} value={h}>
                        {h.toString().padStart(2, '0')}:00
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>End Hour (IST)</span>
                  <select
                    value={shiftEnd}
                    onChange={(e) => setShiftEnd(Number(e.target.value))}
                    className="form-select"
                  >
                    {[16, 17, 18, 19, 20].map((h) => (
                      <option key={h} value={h}>
                        {h.toString().padStart(2, '0')}:00
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* What-If Weather Scenarios */}
      <ScenarioSelector
        scenarios={scenarios}
        selectedScenarioId={selectedScenarioId}
        onSelectScenario={onSelectScenario}
        onSelectLive={onSelectLive}
        isLoading={isLoading}
      />

      {/* Task Selection Component */}
      <TaskSelector
        catalog={catalog}
        selectedTasks={selectedTasks}
        onChangeSelectedTasks={setSelectedTasks}
      />

      {/* Primary Action Button */}
      <button
        onClick={onGeneratePlan}
        disabled={isLoading || selectedTasks.length === 0}
        className="btn-primary"
        style={{ width: '100%', padding: '0.9rem', fontSize: '1.05rem', opacity: isLoading || selectedTasks.length === 0 ? 0.6 : 1 }}
      >
        <Sparkles size={20} />
        {isLoading ? 'Evaluating Workability & Generating Feasible Schedule...' : "CREATE TODAY'S WORK PLAN"}
      </button>
    </div>
  );
};
