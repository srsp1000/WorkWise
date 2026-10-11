import { useState, useEffect, Component, type ErrorInfo, type ReactNode } from 'react';
import { Header } from './components/Header';
import { SetupPage } from './pages/SetupPage';
import { PlanPage } from './pages/PlanPage';
import { WhyPage } from './pages/WhyPage';
import { BriefPage } from './pages/BriefPage';
import { WhySheet } from './components/WhySheet';
import {
  fetchTasksCatalog,
  fetchScenariosList,
  generateLivePlan,
  generateScenarioPlan,
  reverseGeocode
} from './services/api';
import { LoadingSpinner } from './components/LoadingSpinner';
import type {
  PlanResponse,
  ScenarioItem,
  TaskCatalogItem,
  TaskHourCell,
  TaskItemInput,
  LocationInfo,
} from './types/api';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('WorkWise ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="field-card" style={{ padding: '2.5rem', textAlign: 'center', margin: '2rem auto', maxWidth: 640 }}>
          <h3 style={{ color: 'var(--brand-navy)', marginBottom: '0.75rem', fontSize: '1.2rem', fontWeight: 800 }}>
            Unable to Display Work Plan
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: 1.5 }}>
            {this.state.error?.message || 'A data presentation error occurred while rendering the work schedule.'}
          </p>
          <button
            className="btn-primary"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{ padding: '0.65rem 1.5rem', fontSize: '0.9rem' }}
          >
            Reload Application
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export function App() {
  const [activeTab, setActiveTab] = useState<'setup' | 'plan' | 'why' | 'brief'>('setup');
  const [catalog, setCatalog] = useState<Record<string, TaskCatalogItem>>({});
  const [grapStages, setGrapStages] = useState<Record<number, string>>({});
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('normal');
  const [location, setLocation] = useState<LocationInfo>({ lat: 28.6139, lon: 77.2090, city: 'Delhi NCR', state: 'Delhi' });

  const [crewSize, setCrewSize] = useState<number>(18);
  const [newCrew, setNewCrew] = useState<boolean>(false);
  const [grapStage, setGrapStage] = useState<number>(0);
  const [shiftStart, setShiftStart] = useState<number>(6);
  const [shiftEnd, setShiftEnd] = useState<number>(18);

  const [selectedTasks, setSelectedTasks] = useState<TaskItemInput[]>([
    { id: 'concrete', duration_h: 3, crew_required: 8 },
    { id: 'rebar', duration_h: 4, crew_required: 6 },
    { id: 'brickwork', duration_h: 3, crew_required: 5 },
    { id: 'material_prep', duration_h: 2, crew_required: 3 },
  ]);

  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [selectedCell, setSelectedCell] = useState<TaskHourCell | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const { latitude, longitude } = pos.coords;
          try {
            const { city, state } = await reverseGeocode(latitude, longitude);
            setLocation({ lat: latitude, lon: longitude, city, state });
          } catch (e) {
            setLocation({ lat: latitude, lon: longitude, city: 'Unknown', state: 'Unknown' });
          }
        },
        () => { /* Keep default Delhi */ }
      );
    }
  }, []);

  // Load catalog & scenarios on mount
  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [catData, scData] = await Promise.all([
          fetchTasksCatalog(),
          fetchScenariosList(),
        ]);
        setCatalog(catData.tasks);
        setGrapStages(catData.grap_stages);
        setScenarios(scData);

        // Generate initial plan from normal scenario for instant demonstration
        const initPlan = await generateScenarioPlan('normal', {
          lat: 28.6139,
          lon: 77.2090,
          new_crew: false,
          grap_stage: 0,
          shift_start_hour: 6,
          shift_end_hour: 18,
          total_crew_size: 18,
          max_concurrent_tasks: 2,
          tasks: [
            { id: 'concrete', duration_h: 3, crew_required: 8 },
            { id: 'rebar', duration_h: 4, crew_required: 6 },
            { id: 'brickwork', duration_h: 3, crew_required: 5 },
            { id: 'material_prep', duration_h: 2, crew_required: 3 },
          ],
        });
        setPlan(initPlan);
      } catch (err: any) {
        console.warn('Backend API notice:', err.message);
        setError('Backend API is connecting... Ensure uvicorn server is running on http://127.0.0.1:8008');
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  // Handle Scenario Switcher
  const handleSelectScenario = async (scId: string) => {
    setSelectedScenarioId(scId);
    try {
      setIsLoading(true);
      setError(null);
      const res = await generateScenarioPlan(scId, {
        lat: location.lat,
        lon: location.lon,
        new_crew: newCrew,
        grap_stage: grapStage,
        shift_start_hour: shiftStart,
        shift_end_hour: shiftEnd,
        total_crew_size: crewSize,
        max_concurrent_tasks: 2,
        tasks: selectedTasks,
      });
      setPlan(res);
      setActiveTab('plan');
    } catch (err: any) {
      setError(err.message || 'Failed to generate scenario plan');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Generate Live Plan
  const handleGeneratePlan = async () => {
    try {
      setIsLoading(true);
      setError(null);
      let res: PlanResponse;
      const todayDate = new Date().toLocaleDateString('en-CA');
      if (selectedScenarioId && selectedScenarioId !== 'live') {
        res = await generateScenarioPlan(selectedScenarioId, {
          lat: location.lat,
          lon: location.lon,
          new_crew: newCrew,
          grap_stage: grapStage,
          shift_start_hour: shiftStart,
          shift_end_hour: shiftEnd,
          total_crew_size: crewSize,
          max_concurrent_tasks: 2,
          tasks: selectedTasks,
        });
      } else {
        res = await generateLivePlan({
          lat: location.lat,
          lon: location.lon,
          date_str: todayDate,
          new_crew: newCrew,
          grap_stage: grapStage,
          shift_start_hour: shiftStart,
          shift_end_hour: shiftEnd,
          total_crew_size: crewSize,
          max_concurrent_tasks: 2,
          tasks: selectedTasks,
        });
      }
      setPlan(res);
      setActiveTab('plan');
    } catch (err: any) {
      setError(err.message || 'Failed to generate plan');
    } finally {
      setIsLoading(false);
    }
  };

  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const handleApplyAction = async (_actionId: string, payload?: any) => {
    if (!payload) return;
    try {
      setIsLoading(true);
      setError(null);
      setSuccessBanner(null);

      let updatedTasks = [...selectedTasks];

      if (payload.action_type === 'early_concrete' || _actionId === 'early-concrete') {
        const rebarId = payload.task_id || 'rebar';
        let found = false;
        updatedTasks = updatedTasks.map((t) => {
          if (t.id === rebarId) {
            found = true;
            return { ...t, completed_prior: true };
          }
          return t;
        });
        if (!found) {
          updatedTasks.push({ id: rebarId, duration_h: 4, crew_required: 0, completed_prior: true });
        }
      }

      if (payload.set_completed_prior) {
        const targetId = payload.task_id || payload.target_task_id;
        let found = false;
        updatedTasks = updatedTasks.map((t) => {
          if (t.id === targetId) {
            found = true;
            return { ...t, completed_prior: true };
          }
          return t;
        });
        if (!found && targetId) {
          updatedTasks.push({ id: targetId, duration_h: 2, crew_required: 0, completed_prior: true });
        }
      }

      if (payload.set_continuous !== undefined && payload.task_id) {
        updatedTasks = updatedTasks.map((t) => {
          if (t.id === payload.task_id) {
            return { ...t, continuous: payload.set_continuous };
          }
          return t;
        });
      }

      setSelectedTasks(updatedTasks);

      const todayDate = new Date().toLocaleDateString('en-CA');
      const requestPayload = {
        lat: location.lat,
        lon: location.lon,
        date_str: todayDate,
        new_crew: newCrew,
        grap_stage: grapStage,
        shift_start_hour: shiftStart,
        shift_end_hour: shiftEnd,
        total_crew_size: crewSize,
        max_concurrent_tasks: 2,
        tasks: updatedTasks,
      };

      let res: PlanResponse;
      if (selectedScenarioId && selectedScenarioId !== 'live') {
        res = await generateScenarioPlan(selectedScenarioId, requestPayload);
      } else {
        res = await generateLivePlan(requestPayload);
      }
      setPlan(res);
      setSuccessBanner(`Applied recommendation and validated regenerated schedule.`);
      setActiveTab('plan');
    } catch (err: any) {
      setError(err.message || 'Failed to apply recommendation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectLive = () => {
    setSelectedScenarioId('live');
  };

  const taskLabels: Record<string, string> = {};
  Object.values(catalog).forEach((t) => {
    taskLabels[t.id] = t.label;
  });

  return (
    <div className="app-container">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} grapStage={grapStage} />

      {successBanner && (
        <div
          style={{
            background: 'var(--state-go-bg)',
            border: '1px solid var(--state-go-border)',
            color: 'var(--state-go)',
            padding: '0.8rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            marginBottom: '1.25rem',
            fontSize: '0.88rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontWeight: 600,
          }}
        >
          <span>✓ {successBanner}</span>
          <button
            onClick={() => setSuccessBanner(null)}
            style={{ background: 'none', border: 'none', color: 'var(--state-go)', cursor: 'pointer', fontWeight: 700 }}
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#b91c1c',
            padding: '0.8rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            marginBottom: '1.25rem',
            fontSize: '0.88rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', color: '#b91c1c', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      )}

      <ErrorBoundary>
        <main>
          {isLoading && <LoadingSpinner />}
          {activeTab === 'setup' && (
            <SetupPage
              location={location}
              onLocationChange={setLocation}
              catalog={catalog}
              grapStages={grapStages}
              scenarios={scenarios}
              selectedScenarioId={selectedScenarioId}
              onSelectScenario={handleSelectScenario}
              onSelectLive={handleSelectLive}
              crewSize={crewSize}
              setCrewSize={setCrewSize}
              newCrew={newCrew}
              setNewCrew={setNewCrew}
              grapStage={grapStage}
              setGrapStage={setGrapStage}
              shiftStart={shiftStart}
              setShiftStart={setShiftStart}
              shiftEnd={shiftEnd}
              setShiftEnd={setShiftEnd}
              selectedTasks={selectedTasks}
              setSelectedTasks={setSelectedTasks}
              onGeneratePlan={handleGeneratePlan}
              isLoading={isLoading}
            />
          )}

          {activeTab === 'plan' && (
            <PlanPage
              plan={plan}
              city={location.city}
              taskLabels={taskLabels}
              onSelectCell={(cell) => setSelectedCell(cell)}
              onSelectTaskId={(taskId) => {
                if (!plan) return;
                let worstCell = plan.matrix?.[0]?.tasks?.[taskId];
                let maxWbgt = -999;
                for (const row of (plan.matrix || [])) {
                  const cell = row.tasks?.[taskId];
                  if (cell && cell.wbgt_c !== null && cell.wbgt_c > maxWbgt) {
                    maxWbgt = cell.wbgt_c;
                    worstCell = cell;
                  }
                }
                if (worstCell) setSelectedCell(worstCell);
              }}
              onApplyAction={handleApplyAction}
            />
          )}

          {activeTab === 'why' && (
            <WhyPage
              plan={plan}
            />
          )}

          {activeTab === 'brief' && <BriefPage plan={plan} city={location.city} />}
        </main>
      </ErrorBoundary>

      {/* Interactive Diagnostic Modal */}
      <WhySheet cell={selectedCell} onClose={() => setSelectedCell(null)} />
    </div>
  );
}

export default App;
