import math
from datetime import datetime
from typing import Optional


def _solar_cos_zenith(dt: datetime, lat_deg: float, lon_deg: float) -> float:
    """Approximate cosine of solar zenith for a timezone-aware datetime.
    """
    # Convert to local clock hour while keeping India-friendly fixed offset from UTC.

    if dt.tzinfo is None:
        from zoneinfo import ZoneInfo
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))

    # NOAA-style fractional year approximation.
    n = dt.timetuple().tm_yday
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    gamma = 2.0 * math.pi / 365.0 * (n - 1 + (hour - 12.0) / 24.0)

    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    utc_offset_min = dt.utcoffset().total_seconds() / 60.0 if dt.utcoffset() is not None else 330.0
    time_offset = eqtime + 4.0 * lon_deg - utc_offset_min
    tst = hour * 60.0 + time_offset
    solar_hour_angle = (tst / 4.0) - 180.0
    if solar_hour_angle < -180:
        solar_hour_angle += 360.0

    lat = math.radians(lat_deg)
    ha = math.radians(solar_hour_angle)
    cos_zenith = (
        math.sin(lat) * math.sin(decl)
        + math.cos(lat) * math.cos(decl) * math.cos(ha)
    )
    return max(-1.0, min(1.0, cos_zenith))


def _simple_wbgt_c(temp_c: float, rh: float) -> float:
    """Fallback approximation using air temperature and humidity only.

    """
    # Stull wet-bulb approximation, then a simple outdoor sun adder.
    t = temp_c
    tw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )
    # Conservative simple outdoor approximation when no radiation term is available.
    return 0.7 * tw + 0.3 * t


def calculate_wbgt_c(
    temp_c: float,
    rh_pct: float,
    pressure_hpa: float,
    wind_ms: float,
    shortwave_wm2: float,
    direct_wm2: float,
    dt: datetime,
    lat: float,
    lon: float,
) -> tuple[float, str]:
    """Return (WBGT C, method).

    Preferred: thermofeel's physically based Liljegren method.
    Fallback: simple T/RH approximation when thermofeel is unavailable.
    """
    try:
        from thermofeel import calculate_wbgt_liljegren

        cosz = _solar_cos_zenith(dt, lat, lon)
        sw = max(0.0, float(shortwave_wm2))
        direct = max(0.0, float(direct_wm2))
        frac = 0.0 if sw <= 1.0 else min(0.9, max(0.0, direct / sw))
        out_k = calculate_wbgt_liljegren(
            temp_c + 273.15,
            rh_pct,
            pressure_hpa,
            max(0.0, wind_ms),
            sw,
            frac,
            cosz,
        )
        wbgt_c = float(out_k) - 273.15
        if math.isfinite(wbgt_c):
            return wbgt_c, "Liljegren/thermofeel"
    except Exception:
        pass

    return _simple_wbgt_c(temp_c, rh_pct), "simple fallback"
