from dataclasses import dataclass


@dataclass(frozen=True)
class TaskConfig:
    id: str
    label: str
    intensity: str
    default_duration_h: int
    outdoor: bool = True
    continuous: bool = True
    dust_generating: bool = False
    depends_on: tuple[str, ...] = ()
    crew_required: int = 4


# Prototype task catalog. These are workload buckets, not legal classifications.
TASKS = {
    "concrete": TaskConfig("concrete", "Concrete pour", "heavy", 3, True, True, True, ("rebar",), 8),
    "rebar": TaskConfig("rebar", "Rebar work", "heavy", 4, True, True, False, ("excavation",), 6),
    "brickwork": TaskConfig("brickwork", "Brickwork", "moderate", 3, True, True, True, ("concrete",), 5),
    "painting": TaskConfig("painting", "Painting", "moderate", 2, True, True, False, ("brickwork",), 3),
    "material_prep": TaskConfig("material_prep", "Material preparation", "light", 2, False, False, False, (), 3),
    "excavation": TaskConfig("excavation", "Excavation", "heavy", 3, True, True, True, (), 6),
    "crane_lift": TaskConfig("crane_lift", "Crane lift", "heavy", 2, True, True, False, (), 4),
    "electrical": TaskConfig("electrical", "Electrical work", "moderate", 2, True, True, False, (), 3),
    "work_at_height": TaskConfig("work_at_height", "Work at height", "moderate", 2, True, True, False, (), 4),
}

# Graded Response Action Plan (GRAP) for Delhi NCR.
# Stages III and IV prohibit dust-generating construction activities.
GRAP_STAGES = {
    0: "Normal (No Restrictions)",
    1: "Stage I — Poor (Dust Control Enforced)",
    2: "Stage II — Very Poor (Increased Sweeping)",
    3: "Stage III — Severe (Construction & Demolition Banned)",
    4: "Stage IV — Severe+ (Full Vehicle & Site Lockdown)",
}

# Provisional screening values for the prototype.
# The product should move to a source/versioned limits file after expert review.
# They intentionally mirror the blueprint's approximate screening bands.
ACCLIMATED_LIMITS_C = {
    "light": 30.0,
    "moderate": 28.0,
    "heavy": 26.0,
}

UNACCLIMATED_LIMITS_C = {
    "light": 28.0,
    "moderate": 26.0,
    "heavy": 24.0,
}

# State cut-offs are product assumptions, not official medical/legal categories.
STATE_BANDS = (
    ("GO", 0.0),
    ("EASE", -2.0),
    ("LIMIT", -4.0),
    ("STOP", float("-inf")),
)

# Demo-level gates. Equipment/site manuals must override these in a real deployment.
RAIN_PROB_BLOCK = 50.0
RAIN_MM_BLOCK = 0.5
GUST_WARN_KMH = 35.0

