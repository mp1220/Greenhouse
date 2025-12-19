# greenhouse_gateway/enrich/season_context.py

from typing import Dict


def enrich_season() -> Dict[str, object]:
    """
    Biological and long-term season metadata.
    Placeholder until plant-specific logic or AI exists.
    """
    return {
        "biological_phase": None,
        "growth_stage": None,
    }
