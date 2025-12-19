# greenhouse_intelligence/baseline/fan_ranges.py

FAN_RANGES = {
    "circulation_fan": {
        "OFF": (0, 0),
        "LOW": (80, 145),
        "MED": (145, 200),
        "HIGH": (200, 255),
    },
    "exhaust_fan": {
        "OFF": (0, 0),
        "LOW": (100, 150),
        "MED": (150, 200),
        "HIGH": (200, 255),
    },
}
