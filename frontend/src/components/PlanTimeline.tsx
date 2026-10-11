import React from 'react';
import type { PlanResponse } from '../types/api';
import { Calendar, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface PlanTimelineProps {
  plan: PlanResponse;
  onSelectTask?: (taskId: string) => void;
}

export const PlanTimeline: React.FC<PlanTimelineProps> = ({ plan, onSelectTask }) => {
  const { schedule, matrix } = plan;

  // Extract shift window bounds
  const startHour = matrix.length > 0 ? new Date(matrix[0].time).getHours() : 6;
  const endHour = matrix.length > 0 ? new Date(matrix[matrix.length - 1].time).getHours() + 1 : 18;
  const totalHours = Math.max(1, endHour - startHour);

  // Hour boundary ticks
  const hourTicks = [];
  for (let h = startHour; h <= endHour; h++) {
    hourTicks.push(`${h.toString().padStart(2, '0')}:00`);
  }

  const getBarColor = (worstState?: string) => {
    switch (worstState) {
      case 'GO':
        return '#059669'; // Emerald
      case 'EASE':
        return '#d97706'; // Amber
      case 'LIMIT':
        return '#ea580c'; // Tangerine
      case 'STOP':
        return '#dc2626'; // Crimson
      default:
        return '#2563eb';
    }
  };

  return (
    <div className="field-card">
      <div className="field-card-header">
        <div className="field-card-title">
          <Calendar size={20} className="text-blue-700" />
          <span>Proposed Construction Work Schedule (Gantt View)</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Configured Shift Window: {startHour}:00 – {endHour}:00
        </span>
      </div>

      {/* Gantt Timeline Chart */}
      <div className="timeline-track-wrap">
        {/* Hour Header Bar */}
        <div style={{ display: 'flex', borderBottom: '2px solid var(--border-light)', paddingBottom: '0.4rem', marginBottom: '0.6rem', minWidth: 620 }}>
          <div style={{ width: 170, flexShrink: 0, fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
            ACTIVITY
          </div>
          <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, paddingLeft: 4, paddingRight: 4 }}>
            {hourTicks.map((tick) => (
              <span key={tick}>{tick.substring(0, 2)}:00</span>
            ))}
          </div>
        </div>

        {/* Task Rows */}
        <div style={{ minWidth: 620 }}>
          {schedule.map((item) => {
            const isScheduled = item.status === 'SCHEDULED' && item.start && item.end;
            let leftPct = 0;
            let widthPct = 0;

            if (isScheduled && item.start && item.end) {
              const [sH, sM] = item.start.split(':').map(Number);
              const [eH, eM] = item.end.split(':').map(Number);
              const startVal = sH + sM / 60;
              const endVal = eH + eM / 60;

              leftPct = Math.max(0, ((startVal - startHour) / totalHours) * 100);
              widthPct = Math.min(100 - leftPct, ((endVal - startVal) / totalHours) * 100);
            }

            return (
              <div key={item.task_id} className="timeline-row-item">
                <div className="timeline-task-name">
                  <div>{item.task}</div>
                  <div style={{ fontSize: '0.72rem', color: isScheduled ? 'var(--state-go-text)' : 'var(--state-stop-text)' }}>
                    {isScheduled ? `${item.start} – ${item.end}` : 'UNSCHEDULABLE'}
                  </div>
                </div>

                <div className="timeline-bar-area">
                  {isScheduled ? (
                    <div
                      className="timeline-block"
                      onClick={() => onSelectTask && onSelectTask(item.task_id)}
                      style={{
                        left: `${leftPct}%`,
                        width: `${Math.max(4, widthPct)}%`,
                        background: getBarColor(item.worst_state),
                        cursor: 'pointer',
                      }}
                      title={`${item.task}: ${item.start}–${item.end} (${item.worst_state})`}
                    >
                      <span>{item.task} ({item.start}–{item.end})</span>
                    </div>
                  ) : (
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        background: 'var(--state-stop-bg)',
                        border: '1px dashed var(--state-stop-border)',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--state-stop-text)',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                      }}
                    >
                      Shift blocked or prerequisite unmet
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Task Diagnostic & Rationale List */}
      <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', fontWeight: 800, letterSpacing: '0.04em' }}>
        Task Scheduling Diagnostics
      </h4>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {schedule.map((item) => {
          const isScheduled = item.status === 'SCHEDULED';
          return (
            <div
              key={item.task_id}
              onClick={() => onSelectTask && onSelectTask(item.task_id)}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.8rem',
                padding: '0.85rem 1rem',
                borderRadius: 'var(--radius-sm)',
                background: isScheduled ? '#ffffff' : '#fef2f2',
                border: isScheduled ? '1px solid var(--border-light)' : '1.5px solid #fca5a5',
                cursor: 'pointer',
              }}
            >
              {isScheduled ? (
                <CheckCircle2 size={18} className="text-emerald-700" style={{ marginTop: 2, flexShrink: 0 }} />
              ) : (
                <AlertTriangle size={18} className="text-red-700" style={{ marginTop: 2, flexShrink: 0 }} />
              )}

              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
                  <span style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                    {item.task}
                  </span>
                  {isScheduled ? (
                    <span className={`badge-status ${item.worst_state || 'GO'}`}>
                      {item.start} – {item.end}
                    </span>
                  ) : (
                    <span className="badge-status STOP">UNSCHEDULABLE</span>
                  )}
                </div>

                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
                  {isScheduled ? item.why_scheduled : item.why_unschedulable}
                </p>

                {!isScheduled && item.recommended_action && (
                  <p style={{ fontSize: '0.78rem', color: '#991b1b', marginTop: '0.3rem', fontWeight: 600 }}>
                    <strong>Recommended Action:</strong> {item.recommended_action}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
