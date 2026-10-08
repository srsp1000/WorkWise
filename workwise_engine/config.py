from dataclasses import dataclass


@dataclass(frozen=True)
class TaskConfig:
    id: str
    label: str
    intensity: str
    default_duration_h: int
    outdoor: bool = True
    continuous: bool = True


# Prototype task catalog. These are workload buckets, not legal classifications.
TASKS = {
    "concrete": TaskConfig("concrete", "Concrete pour", "heavy", 3, True, True),
    "rebar": TaskConfig("rebar", "Rebar work", "heavy", 4, True, True),
    "brickwork": TaskConfig("brickwork", "Brickwork", "moderate", 3, True, True),
    "painting": TaskConfig("painting", "Painting", "moderate", 2, True, True),
    "material_prep": TaskConfig("material_prep", "Material preparation", "light", 2, False, False),
    "excavation": TaskConfig("excavation", "Excavation", "heavy", 3, True, True),
    "crane_lift": TaskConfig("crane_lift", "Crane lift", "heavy", 2, True, True),
    "electrical": TaskConfig("electrical", "Electrical work", "moderate", 2, True, True),
    "work_at_height": TaskConfig("work_at_height", "Work at height", "moderate", 2, True, True),
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

