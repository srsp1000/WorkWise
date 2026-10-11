import React from 'react';
import type { ScenarioItem } from '../types/api';
import { Sun, CloudRain, Flame, Wind, Radio, CloudSun } from 'lucide-react';

interface ScenarioSelectorProps {
  scenarios: ScenarioItem[];
  selectedScenarioId: string;
  onSelectScenario: (id: string) => void;
  onSelectLive: () => void;
  isLoading: boolean;
}

const SCENARIO_ICONS: Record<string, React.ReactNode> = {
  normal: <Sun size={18} className="text-amber-500" />,
  heatwave: <Flame size={18} className="text-red-500" />,
  cloudburst: <CloudRain size={18} className="text-blue-500" />,
  smog_grap3: <Wind size={18} className="text-purple-600" />,
  monsoon: <CloudSun size={18} className="text-teal-600" />,
};

export const ScenarioSelector: React.FC<ScenarioSelectorProps> = ({
  scenarios,
  selectedScenarioId,
  onSelectScenario,
  onSelectLive,
  isLoading,
}) => {
  return (
    <div className="field-card">
      <div className="field-card-header">
        <div className="field-card-title">
          <Radio size={20} className="text-blue-700" />
          <span>Weather Input & What-If Simulation Scenarios</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
          {selectedScenarioId === 'live' ? 'Live Forecast Active' : `Scenario: ${selectedScenarioId}`}
        </span>
      </div>

      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Select live forecast or test schedule sensitivity under verified Indian construction climate conditions.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
        {/* Live Forecast Option */}
        <div
          onClick={() => !isLoading && onSelectLive()}
          style={{
            padding: '0.85rem 1rem',
            borderRadius: 'var(--radius-sm)',
            background: selectedScenarioId === 'live' ? '#eff6ff' : '#ffffff',
            border: selectedScenarioId === 'live' ? '2px solid var(--brand-blue)' : '1px solid var(--border-light)',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            boxShadow: selectedScenarioId === 'live' ? 'var(--shadow-sm)' : 'none',
            transition: 'all 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <Sun size={18} className="text-blue-600" />
            <span style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--brand-navy)' }}>
              Live Open-Meteo Forecast
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.35' }}>
            Real-time hourly forecast for detected site coordinates.
          </p>
        </div>

        {/* Pre-configured Scenarios */}
        {scenarios.map((sc) => {
          const isSelected = sc.id === selectedScenarioId;
          return (
            <div
              key={sc.id}
              onClick={() => !isLoading && onSelectScenario(sc.id)}
              style={{
                padding: '0.85rem 1rem',
                borderRadius: 'var(--radius-sm)',
                background: isSelected ? '#eff6ff' : '#ffffff',
                border: isSelected ? '2px solid var(--brand-blue)' : '1px solid var(--border-light)',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                boxShadow: isSelected ? 'var(--shadow-sm)' : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                {SCENARIO_ICONS[sc.id] || <Sun size={18} />}
                <span style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--brand-navy)' }}>
                  {sc.title}
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.35' }}>
                {sc.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
