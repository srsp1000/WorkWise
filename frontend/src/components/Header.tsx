import React from 'react';
import { HardHat, LayoutDashboard, Calendar, HelpCircle, Volume2 } from 'lucide-react';

interface HeaderProps {
  activeTab: 'setup' | 'plan' | 'why' | 'brief';
  setActiveTab: (tab: 'setup' | 'plan' | 'why' | 'brief') => void;
  grapStage?: number;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  return (
    <header className="app-header">
      <div className="logo-group" onClick={() => setActiveTab('setup')} style={{ cursor: 'pointer' }}>
        <div className="logo-mark">
          <HardHat size={24} />
        </div>
        <div className="logo-text">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <h1>WorkWise</h1>
            <span
              style={{
                fontSize: '0.68rem',
                fontWeight: 700,
                padding: '0.15rem 0.45rem',
                borderRadius: '4px',
                background: '#e0f2fe',
                color: '#0369a1',
                border: '1px solid #bae6fd',
              }}
            >
              FIELD OPS
            </span>
          </div>
          <div className="logo-tagline">
            Construction Workability & Scheduling Assistant
          </div>
        </div>
      </div>

      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${activeTab === 'setup' ? 'active' : ''}`}
          onClick={() => setActiveTab('setup')}
        >
          <LayoutDashboard size={15} />
          <span>Site Setup</span>
        </button>
        <button
          className={`nav-tab-btn ${activeTab === 'plan' ? 'active' : ''}`}
          onClick={() => setActiveTab('plan')}
        >
          <Calendar size={15} />
          <span>Work Plan</span>
        </button>
        <button
          className={`nav-tab-btn ${activeTab === 'why' ? 'active' : ''}`}
          onClick={() => setActiveTab('why')}
        >
          <HelpCircle size={15} />
          <span>Explainability</span>
        </button>
        <button
          className={`nav-tab-btn ${activeTab === 'brief' ? 'active' : ''}`}
          onClick={() => setActiveTab('brief')}
        >
          <Volume2 size={15} />
          <span>Daily Brief</span>
        </button>
      </nav>
    </header>
  );
};
