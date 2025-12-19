# greenhouse_gateway/enrich/weather_context.py

from typing import Dict


def enrich_weather() -> Dict[str, object]:
    """
    External environmental context.
    Stubbed until weather API integration is added.
    """
    return {
        "weather_source": None,
        "cloud_coverage_pct": None,
        "precip_probability_pct": None,
        "forecast_confidence": None,
        "expected_light_trajectory": None,
        "expected_humidity_decay": None,
    }
