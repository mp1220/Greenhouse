# greenhouse_gateway/enrich/time_context.py

from datetime import datetime
from typing import Dict, Optional


def _season_from_day_of_year(doy: int) -> str:
    if 80 <= doy < 172:
        return "spring"
    if 172 <= doy < 264:
        return "summer"
    if 264 <= doy < 355:
        return "fall"
    return "winter"


def _intent_window_from_hour(hour: int) -> str:
    if 6 <= hour < 10:
        return "morning"
    if 10 <= hour < 16:
        return "midday"
    if 16 <= hour < 20:
        return "evening"
    return "night"


def enrich_time(now: Optional[datetime] = None) -> Dict[str, object]:
    """
    Add time-based metadata.
    """
    now = now or datetime.now()

    day_of_year = now.timetuple().tm_yday
    hour = now.hour

    return {
        "local_time": now.isoformat(),
        "day_of_year": day_of_year,
        "season_state": _season_from_day_of_year(day_of_year),
        "intent_window": _intent_window_from_hour(hour),
    }
