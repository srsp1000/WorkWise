import React from 'react';
import type { PlanResponse } from '../types/api';
import { VoiceBrief } from '../components/VoiceBrief';
import { MessageSquare, ClipboardCheck, ShieldCheck } from 'lucide-react';

interface BriefPageProps {
  plan: PlanResponse | null;
  city: string;
}

export const BriefPage: React.FC<BriefPageProps> = ({ plan, city }) => {
  if (!plan) {
    return (
      <div className="field-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
        <MessageSquare size={40} className="text-blue-700" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--brand-navy)' }}>No Active Work Plan</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Configure your site parameters and generate a plan to view and play the daily site audio brief.
        </p>
      </div>
    );
  }

  const now = new Date();

  return (
    <div>
      {/* Site Header Banner */}
      <div
        className="field-card"
        style={{
          background: 'linear-gradient(135deg, #1e293b, #0f172a)',
          color: '#ffffff',
          marginBottom: '1.25rem',
          border: '1px solid #334155',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <ShieldCheck size={22} style={{ color: '#34d399' }} />
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff', margin: 0 }}>
                DAILY WORKFORCE BRIEFING & AUDIO DISPATCH
              </h2>
            </div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', margin: 0 }}>
              Location: <strong style={{ color: '#ffffff' }}>{city}</strong> | Crew:{' '}
              <strong style={{ color: '#ffffff' }}>{plan.total_crew_size} Workers</strong> ({plan.new_crew ? 'Unacclimatized' : 'Acclimatized'}) | {plan.grap_description}
            </p>
          </div>

          <div
            style={{
              padding: '0.4rem 0.85rem',
              fontSize: '0.82rem',
              fontWeight: 700,
              background: 'rgba(255, 255, 255, 0.1)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
            }}
          >
            {now.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
          </div>
        </div>
      </div>

      {/* Main Multimodal Spoken Briefing Player & Directive */}
      <VoiceBrief plan={plan} city={city} />

      {/* Supervisor Safety Protocols Checklist (Print & Operational Verification) */}
      <div className="field-card" style={{ marginTop: '1.25rem' }}>
        <div className="panel-header" style={{ marginBottom: '0.85rem' }}>
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ClipboardCheck size={20} className="text-emerald-700" />
            <span>Site Supervisor Pre-Shift Verification Protocol</span>
          </div>
        </div>

        <div className="grid-2" style={{ gap: '0.75rem' }}>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              padding: '0.75rem 0.9rem',
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            <input type="checkbox" defaultChecked style={{ accentColor: 'var(--state-go)', width: 18, height: 18 }} />
            <span>Spoken audio brief broadcast to morning assembly in Hindi / English</span>
          </label>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              padding: '0.75rem 0.9rem',
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            <input type="checkbox" defaultChecked style={{ accentColor: 'var(--state-go)', width: 18, height: 18 }} />
            <span>Clean, cool potable water points distributed across outdoor workstations</span>
          </label>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              padding: '0.75rem 0.9rem',
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            <input type="checkbox" defaultChecked style={{ accentColor: 'var(--state-go)', width: 18, height: 18 }} />
            <span>Designated shaded canopy rest stations ready with cross-ventilation</span>
          </label>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              padding: '0.75rem 0.9rem',
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            <input type="checkbox" defaultChecked style={{ accentColor: 'var(--state-go)', width: 18, height: 18 }} />
            <span>First aid kit and heat exhaustion emergency contact verified</span>
          </label>
        </div>
      </div>
    </div>
  );
};
export default BriefPage;
