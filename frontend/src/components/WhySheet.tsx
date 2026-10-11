import React from 'react';
import type { TaskHourCell } from '../types/api';
import { X, Thermometer, Info } from 'lucide-react';

interface WhySheetProps {
  cell: TaskHourCell | null;
  onClose: () => void;
}

export const WhySheet: React.FC<WhySheetProps> = ({ cell, onClose }) => {
  if (!cell) return null;

  const hourStr = cell.time
    ? new Date(cell.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
    : '';

  const isDataMissing = cell.state === 'DATA_UNAVAILABLE';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-sheet-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <span className={`badge-status ${cell.state}`}>
              {cell.state}
            </span>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: 'var(--brand-navy)' }}>
                {cell.task} @ {hourStr}
              </h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Workload: {cell.intensity.replace('_', ' ').toUpperCase()} | Exposure: {cell.outdoor ? 'Outdoor (Unshaded)' : 'Shaded / Covered Area'}
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.25rem',
            }}
          >
            <X size={22} />
          </button>
        </div>

        {/* Missing Data State Banner */}
        {isDataMissing && (
          <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', padding: '0.85rem', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', color: '#475569', fontSize: '0.85rem' }}>
            <strong>Missing Weather Variables:</strong> Meteorological forecast variables for this hour are incomplete or unavailable. WorkWise does not fabricate thermal metrics.
          </div>
        )}

        {/* Diagnostic Metrics Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <div style={{ background: 'var(--bg-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
              Calculated WBGT
            </div>
            <div style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--brand-navy)' }}>
              {cell.wbgt_c !== null ? `${cell.wbgt_c.toFixed(1)}°C` : 'N/A'}
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              {cell.outdoor ? 'With solar load' : 'In-shade (zero solar)'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
              Screening Limit
            </div>
            <div style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-secondary)' }}>
              {cell.limit_c.toFixed(1)}°C
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              OSHA/NIOSH {cell.intensity}
            </div>
          </div>

          <div style={{ background: 'var(--bg-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
              Safety Margin
            </div>
            <div
              style={{
                fontSize: '1.35rem',
                fontWeight: 800,
                color: cell.margin_c === null ? 'var(--text-muted)' : cell.margin_c >= 0 ? 'var(--state-go-solid)' : 'var(--state-stop-solid)',
              }}
            >
              {cell.margin_c !== null ? `${cell.margin_c > 0 ? '+' : ''}${cell.margin_c.toFixed(1)}°C` : 'N/A'}
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              {cell.margin_c !== null && cell.margin_c >= 0 ? 'Within limit' : 'Exceeds limit'}
            </div>
          </div>
        </div>

        {/* Work-Rest Protocol Guidance */}
        <div style={{ background: '#f8fafc', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.25rem', fontWeight: 700, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
            <Thermometer size={16} className="text-amber-600" />
            <span>Screening Work-Rest Recommendation</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>
            {cell.work_rest}
          </p>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Algorithm: {cell.wbgt_method}
          </div>
        </div>

        {/* Diagnostic Explanation & Triggered Gates */}
        <div style={{ background: '#ffffff', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem', fontWeight: 700, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
            <Info size={16} className="text-blue-600" />
            <span>Rule Evaluation & Gate Breakdown</span>
          </div>
          <ul style={{ paddingLeft: '1.2rem', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {cell.why && cell.why.length > 0 ? (
              cell.why.map((r, i) => <li key={i}>{r}</li>)
            ) : (
              <li>No safety gate triggered. Conditions satisfy continuous screening limit.</li>
            )}
          </ul>
        </div>

        {/* Explicit Working Assumptions & Safety Disclaimer */}
        <div style={{ background: '#fefce8', border: '1px solid #fef08a', padding: '0.75rem', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.75rem', color: '#713f12' }}>
          <strong>Assumptions & Site Uncertainty:</strong>
          <ul style={{ paddingLeft: '1.1rem', marginTop: '0.2rem' }}>
            {cell.assumptions?.map((asm, i) => (
              <li key={i}>{asm}</li>
            ))}
          </ul>
        </div>

        {/* Authoritative Standard Citations */}
        <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '0.65rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          <span>References: OSHA OTM Sec III Ch 4 • NIOSH (2016) • CAQM GRAP (Sep 2026)</span>
          <button
            onClick={onClose}
            style={{
              background: 'var(--brand-navy)',
              color: '#ffffff',
              border: 'none',
              padding: '0.35rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
