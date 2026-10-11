import React, { useEffect, useState } from 'react';
import { Droplets, Wind, CloudSun, Sun, CloudRain, CloudLightning, Cloud } from 'lucide-react';
import type { CurrentWeather } from '../types/api';
import { fetchCurrentWeather } from '../services/api';

interface WeatherDashboardProps {
  lat: number;
  lon: number;
  city: string;
}

export const WeatherDashboard: React.FC<WeatherDashboardProps> = ({ lat, lon, city }) => {
  const [weather, setWeather] = useState<CurrentWeather | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const loadWeather = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchCurrentWeather(lat, lon);
        if (mounted) setWeather(data);
      } catch (err) {
        if (mounted) setError('Live weather unavailable. Using offline meteorological baselines.');
      } finally {
        if (mounted) setLoading(false);
      }
    };

    if (lat && lon) {
      loadWeather();
    }
    return () => {
      mounted = false;
    };
  }, [lat, lon]);

  const getWeatherIcon = (code: number, size = 28) => {
    if (code <= 1) return <Sun size={size} className="text-amber-500" />;
    if (code <= 3) return <CloudSun size={size} className="text-amber-600" />;
    if (code === 45 || code === 48) return <Cloud size={size} className="text-slate-400" />;
    if (code >= 51 && code <= 65) return <CloudRain size={size} className="text-blue-500" />;
    if (code >= 80 && code <= 82) return <CloudRain size={size} className="text-blue-600" />;
    if (code >= 95 && code <= 99) return <CloudLightning size={size} className="text-purple-600" />;
    return <CloudSun size={size} className="text-slate-500" />;
  };

  if (loading) {
    return (
      <div className="field-card" style={{ padding: '0.9rem 1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        Retrieving local meteorological forecast...
      </div>
    );
  }

  if (error || !weather) {
    return (
      <div className="field-card" style={{ padding: '0.85rem 1.25rem', background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', fontSize: '0.85rem' }}>
        {error || 'Live weather unavailable.'}
      </div>
    );
  }

  return (
    <div className="field-card" style={{ padding: '0.9rem 1.25rem', marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.85rem' }}>
        {/* Left: Temperature & Conditions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {getWeatherIcon(weather.weather_code, 36)}
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--brand-navy)', lineHeight: 1 }}>
                {weather.temperature.toFixed(1)}°C
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                Feels like {weather.feels_like?.toFixed(1) || weather.temperature.toFixed(1)}°C
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, marginTop: '0.15rem' }}>
              {city} • {weather.description} (IST)
            </div>
          </div>
        </div>

        {/* Center: Contextual Environmental Signals */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem' }}>
            <Droplets size={16} className="text-blue-600" />
            <span style={{ color: 'var(--text-secondary)' }}>Humidity:</span>
            <strong style={{ color: 'var(--brand-navy)' }}>{weather.humidity}%</strong>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem' }}>
            <Wind size={16} className="text-teal-600" />
            <span style={{ color: 'var(--text-secondary)' }}>Wind:</span>
            <strong style={{ color: 'var(--brand-navy)' }}>{weather.wind_speed} km/h</strong>
          </div>

          {/* Air Quality Index (US EPA estimate - labeled as distinct contextual metric) */}
          {weather.aqi !== undefined && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Air Quality (US AQI):</span>
              <strong style={{ color: weather.aqi > 150 ? '#dc2626' : weather.aqi > 100 ? '#ea580c' : '#059669' }}>
                {weather.aqi} ({weather.aqi > 200 ? 'Very Poor' : weather.aqi > 100 ? 'Moderate/Unhealthy' : 'Good'})
              </strong>
            </div>
          )}
        </div>

        {/* Right: Attribution */}
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'right' }}>
          Open-Meteo Hourly Forecast
        </div>
      </div>
    </div>
  );
};
