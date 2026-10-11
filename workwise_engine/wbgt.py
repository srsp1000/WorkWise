"""WorkWise Wet-Bulb Globe Temperature (WBGT) Calculation Engine.

Implements outdoor and indoor/shaded heat stress screening metrics:
1. Primary physically based method: Liljegren et al. (2008) via ECMWF `thermofeel` library.
   Models natural wet bulb temperature, globe temperature under solar irradiance (or zero solar for shade),
   and ambient dry bulb temperature.
2. Deterministic fallback method: Stull (2011) wet-bulb psychrometric formula:
   - Outdoor WBGT: 0.7 * Tw + 0.2 * Tg + 0.1 * Td (with solar radiation black globe adder)
   - Shaded/Indoor WBGT: 0.7 * Tw + 0.3 * Td (zero solar radiation, physics-based shaded exposure)

References:
- Liljegren, J. C., et al. (2008). Modeling the wet bulb globe temperature using standard
  meteorological measurements. Journal of Occupational and Environmental Hygiene, 5(10), 645-655.
- Stull, R. (2011). Wet-bulb temperature from relative humidity and air temperature.
  Journal of Applied Meteorology and Climatology, 50(11), 2267-2269.
- ISO 7243:2017: Assessment of heat stress using the WBGT index.
"""

from __future__ import annotations
import math
from datetime import datetime
from typing import Optional


def _solar_cos_zenith(dt: datetime, lat_deg: float, lon_deg: float) -> float:
    """Calculate the cosine of the solar zenith angle for a given time and location.

    Uses the NOAA solar position algorithm approximation.
    Handles timezone-aware datetimes; for naive datetimes, estimates local standard
    meridian from longitude if no timezone is attached.
    """
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        utc_offset_min = dt.utcoffset().total_seconds() / 60.0
    else:
        # For India sites (lon ~ 68° to 97°), standard meridian is 82.5° (+330 min / IST).
        if 65.0 <= lon_deg <= 100.0 and 5.0 <= lat_deg <= 40.0:
            utc_offset_min = 330.0  # IST (UTC+5:30)
        else:
            utc_offset_min = round(lon_deg / 15.0) * 60.0

    # Day of year and fractional hour
    n = dt.timetuple().tm_yday
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # Fractional year in radians
    gamma = 2.0 * math.pi / 365.0 * (n - 1 + (hour - 12.0) / 24.0)

    # Equation of time in minutes (Spencer 1971)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    # Solar declination angle in radians
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    # True solar time (TST) in minutes
    time_offset = eqtime + 4.0 * lon_deg - utc_offset_min
    tst = hour * 60.0 + time_offset

    # Solar hour angle in degrees
    solar_hour_angle = (tst / 4.0) - 180.0
    while solar_hour_angle < -180.0:
        solar_hour_angle += 360.0
    while solar_hour_angle > 180.0:
        solar_hour_angle -= 360.0

    lat_rad = math.radians(lat_deg)
    ha_rad = math.radians(solar_hour_angle)

    cos_zenith = (
        math.sin(lat_rad) * math.sin(decl)
        + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    )
    return max(-1.0, min(1.0, cos_zenith))


def _simple_wbgt_c(temp_c: float, rh_pct: float, solar_w_m2: Optional[float] = None) -> float:
    """Psychrometric wet-bulb temperature via Stull (2011) with physical solar exposure term.

    tw = Wet bulb temperature via Stull (2011)
    Outdoor WBGT ~ 0.7 * tw + 0.2 * tg + 0.1 * td
    Indoor/Shaded WBGT ~ 0.7 * tw + 0.3 * td (standard zero solar irradiance equation)
    """
    t = float(temp_c)
    rh = max(1.0, min(100.0, float(rh_pct)))

    tw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )

    if solar_w_m2 is not None and solar_w_m2 > 0:
        # Outdoor black globe temperature approximation:
        # In full sunlight, black globe exceeds dry bulb proportionally to solar irradiance
        tg = t + 0.01 * min(1200.0, float(solar_w_m2))
        return 0.7 * tw + 0.2 * tg + 0.1 * t
    else:
        # Shaded or indoor physical formulation (zero direct solar radiation)
        return 0.7 * tw + 0.3 * t


def calculate_wbgt_c(
    temp_c: Optional[float],
    rh_pct: Optional[float],
    pressure_hpa: Optional[float],
    wind_ms: Optional[float],
    shortwave_wm2: Optional[float],
    direct_wm2: Optional[float],
    dt: datetime,
    lat: float,
    lon: float,
    outdoor: bool = True,
    indoor_or_shaded: Optional[bool] = None,
) -> tuple[Optional[float], str]:
    """Calculate WBGT in °C and return (wbgt_c, method_description).

    Where weather inputs are missing or invalid, returns (None, 'DATA_UNAVAILABLE')
    without fabricating values.

    For shaded/indoor work (indoor_or_shaded=True or outdoor=False), solar radiation is
    physically modeled as 0 W/m² using the standard in-shade formula (0.7 Tw + 0.3 Td)
    rather than an arbitrary deduction.
    """
    if indoor_or_shaded is not None:
        outdoor = not indoor_or_shaded

    if temp_c is None or rh_pct is None:
        return None, "DATA_UNAVAILABLE"

    try:
        t = float(temp_c)
        rh = float(rh_pct)
        if not (math.isfinite(t) and math.isfinite(rh)):
            return None, "DATA_UNAVAILABLE"
    except (TypeError, ValueError):
        return None, "DATA_UNAVAILABLE"

    # Clamping for physical validity
    t = max(-20.0, min(60.0, t))
    rh = max(1.0, min(100.0, rh))
    p = max(800.0, min(1100.0, float(pressure_hpa) if pressure_hpa is not None else 1013.25))
    w = max(0.2, min(50.0, float(wind_ms) if wind_ms is not None else 1.5))

    if outdoor:
        sw = max(0.0, float(shortwave_wm2) if shortwave_wm2 is not None else 0.0)
        direct = max(0.0, min(sw, float(direct_wm2) if direct_wm2 is not None else sw))
    else:
        # Shaded or indoor work has zero direct solar irradiance
        sw = 0.0
        direct = 0.0

    try:
        from thermofeel import calculate_wbgt_liljegren

        cosz = _solar_cos_zenith(dt, lat, lon) if outdoor else 0.0
        frac = 0.0 if sw <= 1.0 else min(0.95, direct / sw)

        # Liljegren expects Kelvin, hPa, m/s, W/m²
        out_k = calculate_wbgt_liljegren(
            t + 273.15,
            rh,
            p,
            w,
            sw,
            frac,
            cosz,
        )
        wbgt_c = float(out_k) - 273.15
        if math.isfinite(wbgt_c) and -10.0 <= wbgt_c <= 65.0:
            method_desc = (
                "Liljegren/thermofeel (outdoor solar irradiance)"
                if outdoor
                else "Liljegren/thermofeel (shaded / zero solar irradiance)"
            )
            return round(wbgt_c, 2), method_desc
    except Exception:
        pass

    # Deterministic fallback via Stull psychrometric formulation
    fallback_val = _simple_wbgt_c(t, rh, sw if outdoor else None)
    fallback_desc = (
        "Stull wet-bulb + solar radiation approximation (outdoor)"
        if outdoor
        else "Stull indoor/shaded formula (0.7 Tw + 0.3 Td, zero solar)"
    )
    return round(fallback_val, 2), fallback_desc
