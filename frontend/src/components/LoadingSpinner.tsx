import React, { useState, useEffect } from 'react';

const STAGES = [
  "Fetching weather data...",
  "Computing safety thresholds...",
  "Optimizing schedule...",
  "Generating plan..."
];

export const LoadingSpinner: React.FC = () => {
  const [stageIdx, setStageIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStageIdx((prev) => (prev + 1) % STAGES.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="loading-overlay">
      <style>{`
        .spinner-ring {
          width: 60px;
          height: 60px;
          border: 4px solid rgba(59, 130, 246, 0.2);
          border-top-color: var(--accent-blue);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 1.5rem;
        }
      `}</style>
      <div className="field-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2.5rem', background: '#ffffff', boxShadow: 'var(--shadow-lg)' }}>
        <div className="spinner-ring"></div>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--brand-navy)' }}>
          {STAGES[stageIdx]}
        </h3>
      </div>
    </div>
  );
};
