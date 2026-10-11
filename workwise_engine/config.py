"""WorkWise Configuration and Safety Screening Thresholds.

References:
1. OSHA / NIOSH Heat Stress Screening Criteria:
   - OSHA Technical Manual (OTM) Section III: Chapter 4 — Heat Stress.
   - NIOSH (2016) Criteria for a Recommended Standard: Occupational Exposure to Heat
     and Hot Environments. DHHS (NIOSH) Publication No. 2016-106.
     * Recommended Alert Limits (RAL) for unacclimatized workers.
     * Recommended Exposure Limits (REL) for acclimatized workers.
2. ACGIH (2017) Threshold Limit Values (TLVs) and Biological Exposure Indices (BEIs):
   - Heat Stress and Strain Screening Criteria.
3. ISO 7243:2017 Ergonomics of the thermal environment — Assessment of heat stress
   using the WBGT (wet bulb globe temperature) index.
4. CAQM (Commission for Air Quality Management in NCR and Adjoining Areas):
   - Graded Response Action Plan (GRAP) for Delhi NCR (Revised Schedule dated 29 September 2026).
5. IMD (India Meteorological Department):
   - Heatwave meteorological criteria (used for contextual weather awareness, NOT direct occupational safety limits).

Operational Note:
These thresholds represent screening references derived from published occupational heat guidelines.
They serve as conservative engineering baselines for decision support and planning.
Passing a screening check indicates conditions meet configured screening criteria; it does NOT
constitute a guarantee of absolute safety. Site-specific supervision by qualified safety personnel
remains mandatory.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TaskConfig:
    id: str
    label: str
    intensity: str  # "light", "moderate", "heavy", "very_heavy"
    default_duration_h: int
    outdoor: bool = True
    continuous: bool = False
    dust_generating: bool = False
    depends_on: Tuple[str, ...] = ()
    crew_required: int = 4
    equipment_wind_limit_kmh: float = 35.0  # Configurable equipment wind limit
    rain_sensitive: bool = False             # Configurable precipitation wash gate
    source_reference: str = "OSHA / NIOSH Heat Stress Workload Classification"


# Versioned task catalog with configurable workload classifications and engineering constraints.
TASKS: dict[str, TaskConfig] = {
    "concrete": TaskConfig(
        id="concrete",
        label="Concrete pour",
        intensity="heavy",
        default_duration_h=3,
        outdoor=True,
        continuous=True,  # Cold joints form if interrupted (site-configurable)
        dust_generating=True,
        rain_sensitive=True,
        depends_on=("rebar",),
        crew_required=8,
        source_reference="Heavy manual/vibrator placement (NIOSH/OSHA)",
    ),
    "rebar": TaskConfig(
        id="rebar",
        label="Rebar work",
        intensity="heavy",
        default_duration_h=4,
        outdoor=True,
        continuous=False,  # Can pause/resume around peak midday heat
        dust_generating=False,
        rain_sensitive=False,
        depends_on=("excavation",),
        crew_required=6,
        source_reference="Bending, carrying & tying reinforcement steel (NIOSH/OSHA)",
    ),
    "brickwork": TaskConfig(
        id="brickwork",
        label="Brickwork",
        intensity="moderate",  # Configurable to heavy/very_heavy for high-pace masonry
        default_duration_h=3,
        outdoor=True,
        continuous=False,  # Can pause/resume around peak midday heat
        dust_generating=True,
        rain_sensitive=False,
        depends_on=("concrete",),
        crew_required=5,
        source_reference="Masonry bricklaying (OSHA OTM Sec III Ch 4)",
    ),
    "painting": TaskConfig(
        id="painting",
        label="Painting",
        intensity="moderate",
        default_duration_h=2,
        outdoor=True,
        continuous=False,
        dust_generating=False,
        rain_sensitive=True,
        depends_on=("brickwork",),
        crew_required=3,
        source_reference="Exterior/interior wall coating application",
    ),
    "material_prep": TaskConfig(
        id="material_prep",
        label="Material preparation",
        intensity="light",
        default_duration_h=2,
        outdoor=False,  # Indoor or shaded fabrication area
        continuous=False,
        dust_generating=False,
        rain_sensitive=False,
        depends_on=(),
        crew_required=3,
        source_reference="Shaded sorting, tool prep & light fabrication",
    ),
    "excavation": TaskConfig(
        id="excavation",
        label="Excavation",
        intensity="heavy",
        default_duration_h=3,
        outdoor=True,
        continuous=False,
        dust_generating=True,
        rain_sensitive=False,
        depends_on=(),
        crew_required=6,
        source_reference="Earthmoving & trench work",
    ),
    "crane_lift": TaskConfig(
        id="crane_lift",
        label="Crane lift",
        intensity="heavy",
        default_duration_h=2,
        outdoor=True,
        continuous=False,
        dust_generating=False,
        rain_sensitive=False,
        depends_on=(),
        crew_required=4,
        equipment_wind_limit_kmh=35.0,  # Manufacturer crane limit (EN 13000)
        source_reference="Rigging and hoisting operations",
    ),
    "electrical": TaskConfig(
        id="electrical",
        label="Electrical work",
        intensity="moderate",
        default_duration_h=2,
        outdoor=True,
        continuous=False,
        dust_generating=False,
        rain_sensitive=False,
        depends_on=(),
        crew_required=3,
        source_reference="Conduit laying and wiring installation",
    ),
    "work_at_height": TaskConfig(
        id="work_at_height",
        label="Work at height",
        intensity="moderate",
        default_duration_h=2,
        outdoor=True,
        continuous=False,
        dust_generating=False,
        rain_sensitive=False,
        depends_on=(),
        crew_required=4,
        equipment_wind_limit_kmh=35.0,
        source_reference="Scaffolding and facade elevated tasks",
    ),
}

# Standard 4 Workability Tiers for the Primary Heatmap Experience
WORKABILITY_TIERS = [
    {
        "id": "heavy_outdoor",
        "label": "Heavy outdoor work",
        "description": "Continuous heavy physical labor (concrete pour, rebar carrying, excavation)",
        "intensity": "heavy",
        "outdoor": True,
    },
    {
        "id": "moderate_outdoor",
        "label": "Moderate outdoor work",
        "description": "Sustained moderate physical tasks (brickwork, painting, scaffolding)",
        "intensity": "moderate",
        "outdoor": True,
    },
    {
        "id": "light_outdoor",
        "label": "Light outdoor work",
        "description": "Light physical tasks, inspection and site supervision",
        "intensity": "light",
        "outdoor": True,
    },
    {
        "id": "shaded_indoor",
        "label": "Shaded / indoor work",
        "description": "Covered work areas with zero direct solar radiant load",
        "intensity": "moderate",
        "outdoor": False,
    },
]

# CAQM Graded Response Action Plan (GRAP) for Delhi NCR (Revised Schedule: 29 September 2026).
GRAP_STAGES: dict[int, str] = {
    0: "Normal (No Restrictions)",
    1: "Stage I — Poor (Dust Control Enforced)",
    2: "Stage II — Very Poor (Increased Sweeping & Water Sprinkling)",
    3: "Stage III — Severe (Construction & Demolition Banned - CAQM Sep 2026)",
    4: "Stage IV — Severe+ (Full Vehicle & Site Lockdown)",
}

# Screening limits in °C WBGT for continuous work (OSHA / NIOSH screening baseline).
# Acclimatized workers (NIOSH REL / OSHA baseline screening criteria):
ACCLIMATED_LIMITS_C: dict[str, float] = {
    "light": 30.0,       # Metabolic rate ~200 W
    "moderate": 28.0,    # Metabolic rate ~300 W
    "heavy": 26.0,       # Metabolic rate ~400 W
    "very_heavy": 25.0,  # Metabolic rate ~500 W
}

# Unacclimatized / new workers (NIOSH RAL / OSHA baseline screening criteria):
UNACCLIMATED_LIMITS_C: dict[str, float] = {
    "light": 28.0,       # Metabolic rate ~200 W
    "moderate": 25.0,    # Metabolic rate ~300 W (OSHA baseline: 25.0°C)
    "heavy": 23.0,       # Metabolic rate ~400 W (OSHA baseline: 23.0°C)
    "very_heavy": 21.0,  # Metabolic rate ~500 W (OSHA baseline: 21.0°C)
}

# Workability states relative to screening threshold margin (margin_c = limit_c - wbgt_c):
# GO: margin >= 0.0 °C (conditions meet screening criteria for continuous work with hydration)
# EASE: 0.0 > margin >= -1.5 °C (adjusted recovery; 45 min work / 15 min rest screening guidance)
# LIMIT: -1.5 > margin >= -3.0 °C (restricted exposure; 30 min work / 30 min rest screening guidance)
# STOP: margin < -3.0 °C (conditions exceed screening criteria; suspend or reschedule task)
STATE_BANDS = (
    ("GO", 0.0),
    ("EASE", -1.5),
    ("LIMIT", -3.0),
    ("STOP", float("-inf")),
)

# Environmental constraint gate defaults:
DEFAULT_RAIN_PROB_BLOCK: float = 50.0  # Precipitation probability % threshold for rain-sensitive tasks
DEFAULT_RAIN_MM_BLOCK: float = 0.5     # Precipitation rate mm/h threshold for rain-sensitive tasks
DEFAULT_GUST_WARN_KMH: float = 35.0    # Wind gust speed km/h threshold for cranes / height work
LIGHTNING_CODES: set[int] = {95, 96, 97, 98, 99}  # WMO weather codes for thunderstorms

CONFIG_VERSION: str = "2026.2-field-ops"
LAST_REVIEWED_DATE: str = "2026-10-11"
