import React, { useEffect, useState } from 'react';
import { MapPin, RefreshCw, AlertCircle } from 'lucide-react';
import type { LocationInfo, CityItem } from '../types/api';
import { reverseGeocode, fetchCities } from '../services/api';

interface LocationDetectorProps {
  onLocationChange: (loc: LocationInfo) => void;
  location?: LocationInfo;
}

export const LocationDetector: React.FC<LocationDetectorProps> = ({ onLocationChange, location }) => {
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cities, setCities] = useState<CityItem[]>([]);

  useEffect(() => {
    if (!location) {
      detectLocation();
    }
    loadCities();
  }, []);

  const loadCities = async () => {
    try {
      const cityList = await fetchCities();
      setCities(cityList);
    } catch (err) {
      console.error('Failed to load cities', err);
    }
  };

  const detectLocation = () => {
    setDetecting(true);
    setError(null);

    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      setDetecting(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const { city, state } = await reverseGeocode(latitude, longitude);
          onLocationChange({
            lat: latitude,
            lon: longitude,
            city,
            state
          });
        } catch (err) {
          setError('Failed to reverse geocode location');
        } finally {
          setDetecting(false);
        }
      },
      (err) => {
        console.error(err);
        setError('Location access denied or failed.');
        setDetecting(false);
      },
      { timeout: 10000 }
    );
  };

  const handleCitySelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const cityName = e.target.value;
    const city = cities.find(c => c.name === cityName);
    if (city) {
      onLocationChange({
        lat: city.lat,
        lon: city.lon,
        city: city.name,
        state: city.state
      });
      setError(null);
    }
  };

  return (
    <div className="field-card" style={{ border: '1px solid var(--border-light)', marginBottom: '1rem', background: '#ffffff' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '50%',
            background: 'rgba(16, 185, 129, 0.15)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', color: 'var(--state-go)'
          }}>
            <MapPin size={20} />
          </div>
          <div>
            {detecting ? (
              <div style={{ fontWeight: 600 }}>Detecting Location...</div>
            ) : location ? (
              <>
                <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                  {location.city}{location.state ? `, ${location.state}` : ''}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Lat: {location.lat.toFixed(4)}, Lon: {location.lon.toFixed(4)}
                </div>
              </>
            ) : (
              <div style={{ fontWeight: 600 }}>Location Not Set</div>
            )}
          </div>
        </div>

        <button 
          onClick={detectLocation}
          className="nav-tab" 
          disabled={detecting}
          style={{ background: 'rgba(255, 255, 255, 0.05)' }}
        >
          <RefreshCw size={16} className={detecting ? "animate-spin" : ""} style={{ animation: detecting ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="warning-alert" style={{ marginTop: '1rem' }}>
          <AlertCircle size={18} />
          <div style={{ flex: 1 }}>
            <span style={{ fontSize: '0.9rem' }}>{error}</span>
            {cities.length > 0 && (
              <div className="form-group" style={{ marginTop: '0.5rem', marginBottom: 0 }}>
                <select className="form-select" onChange={handleCitySelect} defaultValue="">
                  <option value="" disabled>Select a city manually...</option>
                  {cities.map(c => (
                    <option key={c.name} value={c.name}>{c.name}, {c.state}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
