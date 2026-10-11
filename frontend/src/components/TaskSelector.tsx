import React from 'react';
import type { TaskCatalogItem, TaskItemInput, TaskIntensity } from '../types/api';
import { Check, Clock, Users, Wrench } from 'lucide-react';

interface TaskSelectorProps {
  catalog: Record<string, TaskCatalogItem>;
  selectedTasks: TaskItemInput[];
  onChangeSelectedTasks: (tasks: TaskItemInput[]) => void;
}

export const TaskSelector: React.FC<TaskSelectorProps> = ({
  catalog,
  selectedTasks,
  onChangeSelectedTasks,
}) => {
  const selectedMap = new Map(selectedTasks.map((t) => [t.id, t]));

  const toggleTask = (task: TaskCatalogItem) => {
    if (selectedMap.has(task.id)) {
      onChangeSelectedTasks(selectedTasks.filter((t) => t.id !== task.id));
    } else {
      onChangeSelectedTasks([
        ...selectedTasks,
        {
          id: task.id,
          duration_h: task.default_duration_h,
          intensity: task.intensity,
          continuous: task.continuous,
          completed_prior: false,
          crew_required: task.crew_required,
          depends_on: task.depends_on,
        },
      ]);
    }
  };

  const updateTaskField = (taskId: string, field: string, val: any) => {
    onChangeSelectedTasks(
      selectedTasks.map((t) => {
        if (t.id === taskId) {
          return { ...t, [field]: val };
        }
        return t;
      })
    );
  };

  const updateTaskDuration = (taskId: string, delta: number) => {
    onChangeSelectedTasks(
      selectedTasks.map((t) => {
        if (t.id === taskId) {
          const newDur = Math.max(1, Math.min(8, (t.duration_h || 2) + delta));
          return { ...t, duration_h: newDur };
        }
        return t;
      })
    );
  };

  return (
    <div className="field-card">
      <div className="field-card-header">
        <div className="field-card-title">
          <Wrench size={20} className="text-blue-700" />
          <span>Construction Activities & Task Profiles</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
          {selectedTasks.length} tasks selected for today
        </span>
      </div>

      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Select activities for today's shift. Workload intensity and prerequisite completion states are configurable per task.
      </p>

      {/* Task Chips Grid */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '1.25rem' }}>
        {Object.values(catalog).map((task) => {
          const isSelected = selectedMap.has(task.id);
          return (
            <button
              key={task.id}
              onClick={() => toggleTask(task)}
              style={{
                border: isSelected ? '1.5px solid var(--brand-navy)' : '1px solid var(--border-strong)',
                background: isSelected ? '#ffffff' : 'var(--bg-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.5rem 0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                cursor: 'pointer',
                boxShadow: isSelected ? 'var(--shadow-sm)' : 'none',
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background:
                    task.intensity === 'very_heavy'
                      ? '#dc2626'
                      : task.intensity === 'heavy'
                      ? '#ea580c'
                      : task.intensity === 'moderate'
                      ? '#d97706'
                      : '#059669',
                }}
              />
              <span style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                {task.label}
              </span>
              {isSelected && <Check size={16} className="text-blue-700" />}
            </button>
          );
        })}
      </div>

      {/* Selected Task Customization */}
      {selectedTasks.length > 0 && (
        <div style={{ background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', padding: '1rem', border: '1px solid var(--border-light)' }}>
          <h4 style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', fontWeight: 800, letterSpacing: '0.05em' }}>
            Configure Task Workload & Execution Constraints
          </h4>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {selectedTasks.map((t) => {
              const item = catalog[t.id];
              if (!item) return null;
              const hasPrereq = item.depends_on && item.depends_on.length > 0;

              return (
                <div
                  key={t.id}
                  style={{
                    background: '#ffffff',
                    border: '1px solid var(--border-light)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.85rem 1rem',
                  }}
                >
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.6rem' }}>
                    <div>
                      <span style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--brand-navy)' }}>
                        {item.label}
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                        <span><Users size={12} style={{ display: 'inline', marginRight: 3 }} /> {t.crew_required || item.crew_required} workers</span>
                        <span>{item.outdoor ? 'Outdoor (Direct Sun)' : 'Shaded Area'}</span>
                        {hasPrereq && (
                          <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
                            Depends on: {item.depends_on.map((d) => catalog[d]?.label || d).join(', ')}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Duration Controls */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 3 }}>
                        <Clock size={13} /> Duration:
                      </span>
                      <button
                        onClick={() => updateTaskDuration(t.id, -1)}
                        style={{
                          width: 26,
                          height: 26,
                          borderRadius: 4,
                          background: 'var(--bg-muted)',
                          border: '1px solid var(--border-strong)',
                          cursor: 'pointer',
                          fontWeight: 700,
                        }}
                      >
                        -
                      </button>
                      <span style={{ fontWeight: 800, minWidth: 28, textAlign: 'center', fontSize: '0.9rem' }}>
                        {t.duration_h || item.default_duration_h}h
                      </span>
                      <button
                        onClick={() => updateTaskDuration(t.id, 1)}
                        style={{
                          width: 26,
                          height: 26,
                          borderRadius: 4,
                          background: 'var(--bg-muted)',
                          border: '1px solid var(--border-strong)',
                          cursor: 'pointer',
                          fontWeight: 700,
                        }}
                      >
                        +
                      </button>
                    </div>
                  </div>

                  {/* Operational Settings: Workload Intensity, Continuous, Prior Completion */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-light)', fontSize: '0.8rem' }}>
                    {/* Intensity Selector */}
                    <div>
                      <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.2rem' }}>
                        Workload Intensity
                      </label>
                      <select
                        value={t.intensity || item.intensity}
                        onChange={(e) => updateTaskField(t.id, 'intensity', e.target.value as TaskIntensity)}
                        className="form-select"
                        style={{ padding: '0.35rem 0.5rem', fontSize: '0.8rem' }}
                      >
                        <option value="light">Light (~200W, inspection)</option>
                        <option value="moderate">Moderate (~300W, bricklaying/painting)</option>
                        <option value="heavy">Heavy (~400W, rebar/excavation/concrete)</option>
                        <option value="very_heavy">Very Heavy (~500W, rapid manual placement)</option>
                      </select>
                    </div>

                    {/* Continuous Toggle */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '1rem' }}>
                      <input
                        type="checkbox"
                        id={`cont-${t.id}`}
                        checked={t.continuous !== undefined ? t.continuous : item.continuous}
                        onChange={(e) => updateTaskField(t.id, 'continuous', e.target.checked)}
                        style={{ width: 16, height: 16 }}
                      />
                      <label htmlFor={`cont-${t.id}`} style={{ cursor: 'pointer', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        Enforce continuous placement (no midday pause)
                      </label>
                    </div>

                    {/* Prerequisite Prior Completion Toggle */}
                    {hasPrereq && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '1rem' }}>
                        <input
                          type="checkbox"
                          id={`prior-${t.id}`}
                          checked={bool(t.completed_prior)}
                          onChange={(e) => updateTaskField(t.id, 'completed_prior', e.target.checked)}
                          style={{ width: 16, height: 16, accentColor: '#059669' }}
                        />
                        <label htmlFor={`prior-${t.id}`} style={{ cursor: 'pointer', fontSize: '0.78rem', color: '#065f46', fontWeight: 600 }}>
                          Prerequisites completed in prior shift (start at shift open)
                        </label>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

function bool(val: any): boolean {
  return Boolean(val);
}
