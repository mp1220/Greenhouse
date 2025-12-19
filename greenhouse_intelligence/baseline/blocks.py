# greenhouse_intelligence/baseline/blocks.py

BASELINE_BLOCKS = {
    "CONTROL": {
        "duration_min": 120,
        "fan_intent": {
            "circulation_fan": "OFF",
            "exhaust_fan": "OFF",
        },
    },
    "CONTROL-INT": {
        "duration_min": 15,
        "fan_intent": {
            "circulation_fan": "OFF",
            "exhaust_fan": "OFF",
        },
    },
    "CIRCULATION_LOW": {
        "duration_min": 90,
        "fan_intent": {
            "circulation_fan": "LOW",
            "exhaust_fan": "OFF",
        },
    },
    "CIRCULATION_MED": {
        "duration_min": 90,
        "fan_intent": {
            "circulation_fan": "MED",
            "exhaust_fan": "OFF",
        },
    },
    "CIRCULATION_HIGH": {
        "duration_min": 90,
        "fan_intent": {
            "circulation_fan": "HIGH",
            "exhaust_fan": "OFF",
        },
    },
    "EXHAUST_LOW": {
        "duration_min": 60,
        "fan_intent": {
            "circulation_fan": "OFF",
            "exhaust_fan": "LOW",
        },
    },
    "EXHAUST_MED": {
        "duration_min": 60,
        "fan_intent": {
            "circulation_fan": "OFF",
            "exhaust_fan": "MED",
        },
    },
    "EXHAUST_HIGH": {
        "duration_min": 60,
        "fan_intent": {
            "circulation_fan": "OFF",
            "exhaust_fan": "HIGH",
        },
    },
}

# Explicit run order, so you are not relying on dict ordering.
BASELINE_SEQUENCE = [
    "CONTROL",
    "CIRCULATION_LOW",
    "CONTROL_INT",
    "CIRCULATION_MED",
    "CONTROL_INT",
    "CIRCULATION_HIGH",
    "CONTROL_INT",
    "EXHAUST_LOW",
    "CONTROL_INT",
    "EXHAUST_MED",
    "CONTROL_INT",
    "EXHAUST_HIGH",
    "CONTROL",  # optional: bookend with a long control period
]
