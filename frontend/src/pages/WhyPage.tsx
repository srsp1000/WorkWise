import React, { useState } from 'react';
import type { PlanResponse } from '../types/api';
import { HelpCircle, Info, ChevronDown, ChevronUp, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface WhyPageProps {
  plan: PlanResponse | null;
}

export const WhyPage: React.FC<WhyPageProps> = ({ plan }) => {
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});

  const toggleCard = (taskId: string) => {
    setExpandedCards((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
  };

  const getWorstCell = (taskId: string) => {
    if (!plan) return null;
    let worstCell = null;
    let maxWbgt = -999;
    for (const row of plan.matrix) {
      const cell = row.tasks[taskId];
      if (cell && cell.wbgt_c !== null && cell.wbgt_c > maxWbgt) {
        maxWbgt = cell.wbgt_c;
        worstCell = cell;
      }
    }
    return worstCell;
  };

  const getRuleText = (item: any, worstCell: any) => {
    if (item.status === 'SCHEDULED') {
      return 'Scheduled within configured screening limits derived from OSHA / NIOSH continuous work screening criteria.';
    }
    const why = item.why_unschedulable || '';
    if (why.toLowerCase().includes('grap')) {
      return `CAQM GRAP regulations (revised 29 Sep 2026 schedule) prohibit dust-generating activities at Stage ${plan!.grap_stage}.`;
    }
    if (why.toLowerCase().includes('prereq') || why.toLowerCase().includes('depend')) {
      const match = why.match(/'([^']+)'/) || why.match(/task ([\w-]+)/i);
      const dep = match ? match[1] : 'prerequisite';
      return `Prerequisite task '${dep}' was not scheduled today, blocking this task.`;
    }
    if (worstCell) {
      const durationMatch = why.match(/(\d+)h/i) || why.match(/(\d+)\s*hour/i);
      const duration = durationMatch ? durationMatch[1] : 'X';
      return `No window of ${duration}h exists meeting the ${worstCell.intensity}-workload continuous screening threshold of ${worstCell.limit_c.toFixed(1)}°C WBGT.`;
    }
    return 'Could not be scheduled within configured environmental or site constraints.';
  };

  if (!plan) {
    return (
      <div className="field-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
        <HelpCircle size={40} className="text-blue-700" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--brand-navy)' }}>No Active Work Plan</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Generate a plan first to inspect explainable safety diagnostics and threshold calculations.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="field-card" style={{ marginBottom: '1.25rem' }}>
        <div className="panel-header" style={{ marginBottom: '0.75rem' }}>
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Info size={20} className="text-blue-700" />
            <span>Safety Rule Transparency & Screening Diagnostics</span>
          </div>
        </div>

        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: '1.5', marginBottom: '1rem' }}>
          WorkWise evaluates every task deterministically against physical environmental metrics (Liljegren / ISO 7243 WBGT,
          wind, rainfall, thunderstorm proximity) and regulatory mandates (CAQM GRAP). The screening thresholds used are
          published OSHA / NIOSH continuous work benchmarks. A passing screening score indicates hours meeting criteria,
          not a legal guarantee of absolute safety.
        </p>

        {/* Screening Reference Table */}
        <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', marginBottom: '1.25rem' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--brand-navy)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            OSHA / NIOSH Screening Reference Thresholds (Continuous Work)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', fontSize: '0.75rem' }}>
            <div style={{ background: '#ffffff', padding: '0.4rem 0.6rem', borderRadius: 4, border: '1px solid var(--border-subtle)' }}>
              <strong>Light (200W):</strong> 30°C / 28°C
            </div>
            <div style={{ background: '#ffffff', padding: '0.4rem 0.6rem', borderRadius: 4, border: '1px solid var(--border-subtle)' }}>
              <strong>Moderate (300W):</strong> 28°C / 25°C
            </div>
            <div style={{ background: '#ffffff', padding: '0.4rem 0.6rem', borderRadius: 4, border: '1px solid var(--border-subtle)' }}>
              <strong>Heavy (400W):</strong> 26°C / 23°C
            </div>
            <div style={{ background: '#ffffff', padding: '0.4rem 0.6rem', borderRadius: 4, border: '1px solid var(--border-subtle)' }}>
              <strong>Very Heavy (500W):</strong> 25°C / 21°C
            </div>
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            Format: [Acclimatized] / [Unacclimatized]. WorkWise currently configured for: <strong>{plan.new_crew ? 'Unacclimatized' : 'Acclimatized'}</strong> crew.
          </div>
        </div>

        {/* Task Cards Grid */}
        <div className="grid-2" style={{ gap: '0.85rem' }}>
          {plan.schedule.map((item) => {
            const isExpanded = expandedCards[item.task_id] || false;
            const worstCell = getWorstCell(item.task_id);
            const ruleText = getRuleText(item, worstCell);
            const isScheduled = item.status === 'SCHEDULED';

            return (
              <div
                key={item.task_id}
                onClick={() => toggleCard(item.task_id)}
                style={{
                  background: '#ffffff',
                  border: isScheduled ? '1px solid var(--border-subtle)' : '1px solid #fecaca',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem 1.15rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {isScheduled ? (
                      <CheckCircle2 size={18} className="text-emerald-700" />
                    ) : (
                      <ShieldAlert size={18} style={{ color: 'var(--state-stop)' }} />
                    )}
                    <h4 style={{ fontWeight: 800, fontSize: '0.98rem', color: 'var(--brand-navy)', margin: 0 }}>
                      {item.task}
                    </h4>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span
                      style={{
                        padding: '0.2rem 0.55rem',
                        borderRadius: 4,
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        background: isScheduled ? 'var(--state-go-bg)' : 'var(--state-stop-bg)',
                        color: isScheduled ? 'var(--state-go)' : 'var(--state-stop)',
                        border: `1px solid ${isScheduled ? 'var(--state-go-border)' : 'var(--state-stop-border)'}`,
                      }}
                    >
                      {item.status}
                    </span>
                    {isExpanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
                  </div>
                </div>

                <div style={{ fontSize: '0.82rem', color: isScheduled ? 'var(--text-main)' : '#991b1b', marginTop: '0.4rem', lineHeight: '1.4' }}>
                  {isScheduled ? item.why_scheduled : item.why_unschedulable}
                </div>

                {isExpanded && (
                  <div style={{ marginTop: '0.85rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
                    {worstCell && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--brand-navy)', marginBottom: '0.6rem', fontWeight: 600 }}>
                        Peak Condition: {worstCell.wbgt_c != null ? `${worstCell.wbgt_c.toFixed(1)}°C WBGT` : 'DATA_UNAVAILABLE'} | Limit: {worstCell.limit_c.toFixed(1)}°C | Margin:{' '}
                        {worstCell.margin_c != null ? (
                          <span style={{ color: worstCell.margin_c >= 0 ? 'var(--state-go)' : 'var(--state-stop)' }}>
                            {worstCell.margin_c >= 0 ? '+' : ''}{worstCell.margin_c.toFixed(1)}°C
                          </span>
                        ) : (
                          <span>N/A</span>
                        )}
                      </div>
                    )}

                    <div
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        background: '#f8fafc',
                        padding: '0.5rem 0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      <strong>Deterministic Decision Rule:</strong> {ruleText}
                    </div>

                    {!isScheduled && item.recommended_action && (
                      <div
                        style={{
                          marginTop: '0.5rem',
                          fontSize: '0.75rem',
                          color: '#92400e',
                          background: '#fef3c7',
                          padding: '0.5rem 0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid #fde68a',
                        }}
                      >
                        <strong>Supervisor Action:</strong> {item.recommended_action}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
export default WhyPage;
