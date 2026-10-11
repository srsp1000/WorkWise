import React, { useState } from 'react';
import type { WorkabilityHeatmapRow, TaskHourCell, HourlyMatrixRow } from '../types/api';
import { AlertTriangle, AlertCircle, Ban, HelpCircle, Layers, CheckCircle2 } from 'lucide-react';

interface TaskHeatmapProps {
  workabilityHeatmap?: WorkabilityHeatmapRow[];
  matrix?: HourlyMatrixRow[];
  taskLabels?: Record<string, string>;
  onCellClick: (cell: TaskHourCell) => void;
}

export const TaskHeatmap: React.FC<TaskHeatmapProps> = ({
  workabilityHeatmap = [],
  matrix = [],
  taskLabels = {},
  onCellClick,
}) => {
  const [viewMode, setViewMode] = useState<'tiers' | 'tasks'>('tiers');

  // Extract hours from cells
  const hourLabels =
    workabilityHeatmap?.[0]?.cells?.map((c) => {
      const d = new Date(c.time);
      return `${d.getHours().toString().padStart(2, '0')}:00`;
    }) ||
    matrix?.map((r) => {
      const d = new Date(r.time);
      return `${d.getHours().toString().padStart(2, '0')}:00`;
    }) ||
    [];

  const getStatusIcon = (state: string) => {
    switch (state) {
      case 'GO':
        return <CheckCircle2 size={13} className="text-emerald-700" />;
      case 'EASE':
        return <AlertCircle size={13} className="text-amber-700" />;
      case 'LIMIT':
        return <AlertTriangle size={13} className="text-orange-700" />;
      case 'STOP':
        return <Ban size={13} className="text-red-700" />;
      default:
        return <HelpCircle size={13} className="text-slate-500" />;
    }
  };

  const getStatusShort = (state: string) => {
    switch (state) {
      case 'GO':
        return 'GO';
      case 'EASE':
        return 'EASE';
      case 'LIMIT':
        return 'LIMIT';
      case 'STOP':
        return 'STOP';
      default:
        return 'N/A';
    }
  };

  return (
    <div className="field-card">
      <div className="field-card-header">
        <div>
          <div className="field-card-title">
            <Layers size={20} className="text-blue-700" />
            <span>Workability Heatmap (Primary Screening Experience)</span>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Tap any cell to inspect meteorological inputs, physically modeled WBGT, threshold margin, and screening rules.
          </p>
        </div>

        {/* View Toggle */}
        <div style={{ display: 'flex', gap: '0.35rem', background: 'var(--bg-muted)', padding: '0.2rem', borderRadius: 'var(--radius-sm)' }}>
          <button
            onClick={() => setViewMode('tiers')}
            style={{
              border: 'none',
              background: viewMode === 'tiers' ? '#ffffff' : 'transparent',
              color: viewMode === 'tiers' ? 'var(--brand-navy)' : 'var(--text-muted)',
              fontWeight: 700,
              fontSize: '0.75rem',
              padding: '0.3rem 0.65rem',
              borderRadius: '4px',
              cursor: 'pointer',
              boxShadow: viewMode === 'tiers' ? 'var(--shadow-sm)' : 'none',
            }}
          >
            Workload Tiers
          </button>
          {matrix.length > 0 && (
            <button
              onClick={() => setViewMode('tasks')}
              style={{
                border: 'none',
                background: viewMode === 'tasks' ? '#ffffff' : 'transparent',
                color: viewMode === 'tasks' ? 'var(--brand-navy)' : 'var(--text-muted)',
                fontWeight: 700,
                fontSize: '0.75rem',
                padding: '0.3rem 0.65rem',
                borderRadius: '4px',
                cursor: 'pointer',
                boxShadow: viewMode === 'tasks' ? 'var(--shadow-sm)' : 'none',
              }}
            >
              Selected Tasks
            </button>
          )}
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="heatmap-container">
        <table className="heatmap-table">
          <thead>
            <tr>
              <th className="sticky-col">
                {viewMode === 'tiers' ? 'WORKLOAD / EXPOSURE TIER' : 'SITE ACTIVITY'}
              </th>
              {hourLabels.map((lbl, idx) => (
                <th key={idx}>{lbl}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {viewMode === 'tiers' ? (
              workabilityHeatmap.map((row) => (
                <tr key={row.tier_id}>
                  <td className="sticky-col">
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                      {row.tier_label}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                      {row.outdoor ? 'Outdoor (solar load)' : 'Shaded / Indoor (zero direct solar)'}
                    </div>
                  </td>
                  {row.cells.map((cell, cIdx) => (
                    <td key={cIdx}>
                      <button
                        className={`heatmap-cell-btn state-${cell.state}`}
                        onClick={() => onCellClick(cell)}
                        title={`${cell.task} @ ${new Date(cell.time).getHours()}:00: ${cell.state} (WBGT: ${cell.wbgt_c !== null ? cell.wbgt_c + '°C' : 'N/A'})`}
                      >
                        <span className="cell-state-badge">
                          {getStatusIcon(cell.state)}
                          {getStatusShort(cell.state)}
                        </span>
                        <span className="cell-wbgt-sub">
                          {cell.wbgt_c !== null ? `${cell.wbgt_c.toFixed(1)}°C` : 'No data'}
                        </span>
                      </button>
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              // Task level view
              matrix.length > 0 &&
              matrix[0]?.tasks &&
              Object.keys(matrix[0].tasks).map((tid) => {
                const label = taskLabels[tid] || matrix[0].tasks[tid]?.task || tid;
                return (
                  <tr key={tid}>
                    <td className="sticky-col">
                      <div style={{ fontWeight: 700, fontSize: '0.88rem' }}>{label}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {matrix[0].tasks[tid]?.intensity} workload
                      </div>
                    </td>
                    {matrix.map((row, rIdx) => {
                      const cell = row.tasks[tid];
                      if (!cell) return <td key={rIdx}>-</td>;
                      return (
                        <td key={rIdx}>
                          <button
                            className={`heatmap-cell-btn state-${cell.state}`}
                            onClick={() => onCellClick(cell)}
                            title={`${label} @ ${new Date(cell.time).getHours()}:00: ${cell.state}`}
                          >
                            <span className="cell-state-badge">
                              {getStatusIcon(cell.state)}
                              {getStatusShort(cell.state)}
                            </span>
                            <span className="cell-wbgt-sub">
                              {cell.wbgt_c !== null ? `${cell.wbgt_c.toFixed(1)}°C` : 'No data'}
                            </span>
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Sourced Legend Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-light)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem' }}>
            <span className="badge-status GO">GO</span>
            <span style={{ color: 'var(--text-secondary)' }}>Screening Passed (Normal breaks)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem' }}>
            <span className="badge-status EASE">EASE</span>
            <span style={{ color: 'var(--text-secondary)' }}>Adjusted Recovery (45:15 cycle)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem' }}>
            <span className="badge-status LIMIT">LIMIT</span>
            <span style={{ color: 'var(--text-secondary)' }}>Restricted Exposure (30:30 cycle)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem' }}>
            <span className="badge-status STOP">STOP</span>
            <span style={{ color: 'var(--text-secondary)' }}>Exceeds Limits / Gate Blocked</span>
          </div>
        </div>

        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>
          * Screening guidance based on OSHA / NIOSH continuous work limits. Passing screening is not a safety guarantee.
        </div>
      </div>
    </div>
  );
};
