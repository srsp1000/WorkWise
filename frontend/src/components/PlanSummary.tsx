import React from 'react';
import type { PlanResponse } from '../types/api';
import { Calendar, ShieldAlert } from 'lucide-react';

interface PlanSummaryProps {
  plan: PlanResponse;
  city: string;
}

export const PlanSummary: React.FC<PlanSummaryProps> = ({ plan, city }) => {
  const scheduledCount = plan.schedule.filter(s => s.status === 'SCHEDULED').length;
  const totalCount = plan.schedule.length;

  let peakWbgt = 0;
  let peakTime = '';

  const heatDangerWindow = { start: -1, end: -1 };

  plan.matrix.forEach(row => {
    const hour = new Date(row.time).getHours();
    Object.values(row.tasks).forEach((cell) => {
      if (cell.wbgt_c !== null && cell.wbgt_c > peakWbgt) {
        peakWbgt = cell.wbgt_c;
        peakTime = `${hour.toString().padStart(2, '0')}:00`;
      }
      
      // Rough estimation of danger window based on heavy intensity STOPs
      if (cell.intensity === 'heavy' && cell.state === 'STOP') {
        if (heatDangerWindow.start === -1) heatDangerWindow.start = hour;
        heatDangerWindow.end = hour;
      }
    });
  });

  const totalShiftHours = plan.matrix.length;
  const hoursMeetingScreening = plan.matrix.filter((row) =>
    Object.values(row.tasks).some((cell) => cell.state === 'GO')
  ).length;

  return (
    <div className="field-card" style={{ marginBottom: '1rem' }}>
      <div className="panel-header" style={{ marginBottom: '0.85rem' }}>
        <div className="panel-title">
          <Calendar size={20} className="text-blue-700" />
          <span>Shift Summary for {city}</span>
        </div>
      </div>

      <p style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--brand-navy)', marginBottom: '1rem' }}>
        {scheduledCount} of {totalCount} tasks scheduled. Peak heat index: {peakWbgt.toFixed(1)}°C WBGT at {peakTime}.
      </p>

      {heatDangerWindow.start !== -1 && (
        <div
          style={{
            background: 'var(--state-stop-bg)',
            padding: '0.75rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--state-stop-border)',
            marginBottom: '1rem',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
          }}
        >
          <ShieldAlert size={18} style={{ color: 'var(--state-stop)', flexShrink: 0 }} />
          <span style={{ fontSize: '0.85rem', color: '#991b1b' }}>
            <strong>Screening Exceeded Window (Heavy Outdoor):</strong> {heatDangerWindow.start}:00 - {heatDangerWindow.end + 1}:00
          </span>
        </div>
      )}

      <div className="grid-3">
        <div className="stat-card" style={{ padding: '0.75rem' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--brand-navy)' }}>
            {hoursMeetingScreening} / {totalShiftHours} hrs
          </div>
          <div className="stat-label">Hours Meeting Screening</div>
        </div>
        <div className="stat-card" style={{ padding: '0.75rem' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--brand-navy)' }}>{plan.total_crew_size}</div>
          <div className="stat-label">Total Crew Size</div>
        </div>
        <div className="stat-card" style={{ padding: '0.75rem' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--brand-navy)' }}>Stage {plan.grap_stage}</div>
          <div className="stat-label">CAQM GRAP Status</div>
        </div>
      </div>
    </div>
  );
};
