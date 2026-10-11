import React from 'react';
import type { PlanResponse, TaskHourCell } from '../types/api';
import { TaskHeatmap } from '../components/TaskHeatmap';
import { PlanTimeline } from '../components/PlanTimeline';
import {
  Lightbulb,
  ArrowRight,
  Clock,
  Users,
  Calendar,
  Layers,
} from 'lucide-react';

interface PlanPageProps {
  plan: PlanResponse | null;
  city: string;
  taskLabels: Record<string, string>;
  onSelectCell: (cell: TaskHourCell) => void;
  onSelectTaskId: (taskId: string) => void;
  onApplyAction?: (actionId: string, payload?: any) => void;
}

export const PlanPage: React.FC<PlanPageProps> = ({
  plan,
  city,
  taskLabels,
  onSelectCell,
  onSelectTaskId,
  onApplyAction,
}) => {
  if (!plan) {
    return (
      <div className="field-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
        <Layers size={40} className="text-blue-700" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--brand-navy)' }}>No Active Work Plan</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
          Configure your site parameters and click "CREATE TODAY'S WORK PLAN" to view the workability heatmap and schedule.
        </p>
      </div>
    );
  }

  // Calculate measurable screening metrics (not "safe working time"!)
  const matrix = plan.matrix || [];
  const heatmap = plan.workability_heatmap || [];
  const totalShiftHours = matrix.length;
  const hoursMeetingScreening = matrix.filter((row) =>
    Object.values(row.tasks || {}).some((c) => c.state === 'GO')
  ).length;

  const heavyWorkableHours = heatmap.find((t) => t.tier_id === 'heavy_outdoor')
    ?.cells?.filter((c) => c.state === 'GO' || c.state === 'EASE').length || 0;

  return (
    <div>
      {/* 1. Compact Site / Time / Weather Context */}
      <div className="field-card" style={{ padding: '0.9rem 1.25rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.85rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
              <span className="badge-status GO" style={{ fontSize: '0.72rem', padding: '0.15rem 0.5rem' }}>
                ACTIVE PLAN
              </span>
              <h2 style={{ fontSize: '1.15rem', color: 'var(--brand-navy)', fontWeight: 800 }}>
                {plan.site || city} — Workday Plan
              </h2>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
              <span><Calendar size={13} style={{ display: 'inline', marginRight: 3 }} /> {plan.date}</span>
              <span><Clock size={13} style={{ display: 'inline', marginRight: 3 }} /> Shift: {plan.input_assumptions?.shift_window || '06:00 – 18:00'}</span>
              <span><Users size={13} style={{ display: 'inline', marginRight: 3 }} /> Crew: {plan.total_crew_size} ({plan.new_crew ? 'Unacclimatized' : 'Acclimatized'})</span>
              <span>Air Quality: {plan.grap_description}</span>
            </div>
          </div>

          {/* Contextual Screening Indicators */}
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-light)', padding: '0.4rem 0.75rem', borderRadius: 'var(--radius-sm)', textAlign: 'right' }}>
              <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--brand-navy)' }}>
                {hoursMeetingScreening} of {totalShiftHours} hrs
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                Meeting Screening Criteria
              </div>
            </div>

            <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-light)', padding: '0.4rem 0.75rem', borderRadius: 'var(--radius-sm)', textAlign: 'right' }}>
              <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--brand-navy)' }}>
                {heavyWorkableHours} hrs
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                Heavy Outdoor Window
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. One-Sentence WorkWise Signature Recommendation */}
      <div className="recommendation-banner">
        <Lightbulb size={22} className="text-emerald-700" style={{ flexShrink: 0, marginTop: 2 }} />
        <div className="recommendation-banner-text">
          <div className="recommendation-banner-label">
            WorkWise Operational Recommendation
          </div>
          <div className="recommendation-banner-copy">
            {plan.top_recommendation || plan.plan_summary || 'All planned activities meet configured site screening criteria.'}
          </div>
        </div>
      </div>

      {/* 3. Large, Legible Workability Heatmap (Primary Experience) */}
      <TaskHeatmap
        workabilityHeatmap={heatmap}
        matrix={matrix}
        taskLabels={taskLabels}
        onCellClick={onSelectCell}
      />

      {/* 4. Three Prioritised Recommended Actions */}
      {plan.prioritized_actions && plan.prioritized_actions.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--brand-navy)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Prioritised Operational Actions
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Supervisor decision-support recommendations
            </span>
          </div>

          <div className="prioritized-actions-grid">
            {plan.prioritized_actions.map((act, idx) => (
              <div key={act.id || idx} className="action-card">
                <div>
                  <div className="action-card-header">
                    <div className="action-card-num">{idx + 1}</div>
                    <div className="action-card-title">{act.title}</div>
                  </div>

                  <div className="action-card-body">
                    <strong>Action:</strong> {act.action}
                  </div>

                  <div className="action-card-detail">
                    <div style={{ marginBottom: '0.25rem' }}>
                      <strong>Affected:</strong> {act.affected}
                    </div>
                    <div style={{ marginBottom: '0.25rem' }}>
                      <strong>Rationale:</strong> {act.why}
                    </div>
                    <div style={{ marginBottom: '0.25rem' }}>
                      <strong>Constraint:</strong> {act.constraint}
                    </div>
                    <div>
                      <strong>Feasible Alternative:</strong> {act.alternative}
                    </div>
                  </div>
                </div>

                {act.can_apply && onApplyAction && (
                  <button
                    className="action-apply-btn"
                    onClick={() => onApplyAction(act.id, act.apply_payload)}
                  >
                    <span>Apply Recommendation</span>
                    <ArrowRight size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Proposed Construction Work Schedule (Gantt View + Diagnostic Cards) */}
      <PlanTimeline plan={plan} onSelectTask={onSelectTaskId} />
    </div>
  );
};
