# greenhouse_gateway/data_collector.py

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from ..persist import storage
from ..publish import google_sheets

# Enrichment modules
from ..enrich.time_context import enrich_time
from ..enrich.weather_context import enrich_weather
from ..enrich.season_context import enrich_season

logger = logging.getLogger("greenhouse_gateway.data_collector")

BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = BASE_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

LATEST_PATH = RUNTIME_DIR / "latest_packet.json"


# ---------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------

def normalize_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw ESP32 packet into DB-ready schema.
    Explicit ownership mapping. NULL-safe.
    """

    normalized: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # TIMESTAMP
    # ------------------------------------------------------------------
    normalized["jetson_timestamp"] = packet.get(
        "jetson_timestamp",
        datetime.utcnow().isoformat()
    )

    # ------------------------------------------------------------------
    # INSIDE ENVIRONMENT (SHT4 + TSL2591)
    # ------------------------------------------------------------------
    if "inside_temp_f" in packet:
        normalized["inside_temp_f"] = packet.get("inside_temp_f")

    if "inside_humidity_rh" in packet:
        normalized["inside_humidity_rh"] = packet.get("inside_humidity_rh")

    if "inside_dew_point_f" in packet:
        normalized["inside_dew_point_f"] = packet.get("inside_dew_point_f")

    if "inside_vpd_kpa" in packet:
        normalized["inside_vpd_kpa"] = packet.get("inside_vpd_kpa")

    if "inside_brightness_lux" in packet:
        normalized["inside_brightness_lux"] = packet.get("inside_brightness_lux")

    # ------------------------------------------------------------------
    # TSL2591 RAW (ML input)
    # ------------------------------------------------------------------
    normalized["tsl_full_spectrum"] = packet.get("tsl_full_spectrum")
    normalized["tsl_infrared"] = packet.get("tsl_infrared")

    # ------------------------------------------------------------------
    # OUTSIDE OPTICAL (APDS9960 ONLY)
    # ------------------------------------------------------------------
    if "outside_brightness_raw" in packet:
        normalized["outside_brightness_raw"] = packet.get("outside_brightness_raw")

    if "outside_color_r" in packet:
        normalized["outside_color_r"] = packet.get("outside_color_r")

    if "outside_color_g" in packet:
        normalized["outside_color_g"] = packet.get("outside_color_g")

    if "outside_color_b" in packet:
        normalized["outside_color_b"] = packet.get("outside_color_b")

    # ------------------------------------------------------------------
    # SYSTEM / ACTUATORS
    # ------------------------------------------------------------------
    normalized["circulation_fan_pwm"] = packet.get("circulation_fan_pwm")
    normalized["exhaust_fan_pwm"] = packet.get("exhaust_fan_pwm")
    normalized["grow_light_pwm"] = packet.get("grow_light_pwm")

    normalized["esp32_runtime_ms"] = packet.get("esp32_runtime_ms")
    normalized["firmware_version"] = packet.get("firmware_version")
    normalized["wifi_rssi"] = packet.get("wifi_rssi")
    normalized["mqtt_reconnects"] = packet.get("mqtt_reconnects")

    normalized["disconnected_sensors"] = packet.get("disconnected_sensors")

    return normalized


# ---------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------

def enrich_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(packet)

    try:
        enriched.update(enrich_time())
    except Exception as e:
        logger.exception("Time enrichment failed: %s", e)

    try:
        enriched.update(enrich_weather())
    except Exception as e:
        logger.exception("Weather enrichment failed: %s", e)

    try:
        enriched.update(enrich_season())
    except Exception as e:
        logger.exception("Season enrichment failed: %s", e)

    # Control context
    enriched.setdefault("control_mode", None)
    enriched.setdefault("control_reason", None)

    # Forecast placeholders
    enriched.setdefault("expected_light_trajectory", None)
    enriched.setdefault("expected_humidity_decay", None)
    enriched.setdefault("forecast_confidence", None)

    return enriched


# ---------------------------------------------------------------------
# Runtime snapshot
# ---------------------------------------------------------------------

def save_latest_packet(packet: Dict[str, Any]) -> None:
    try:
        LATEST_PATH.write_text(json.dumps(packet, indent=2))
    except Exception as e:
        logger.exception("Error writing latest_packet.json: %s", e)


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------

def process_packet(packet: Dict[str, Any]) -> None:
    logger.info("Processing new sensor packet")

    normalized = normalize_packet(packet)
    enriched = enrich_packet(normalized)

    try:
        storage.insert_sensor_reading(enriched)
        logger.info("Sensor packet persisted successfully")
    except Exception as e:
        logger.exception("Error inserting sensor reading into DB: %s", e)

    save_latest_packet(enriched)

    try:
        google_sheets.add_packet(enriched)
    except Exception as e:
        logger.exception("Error buffering packet for Google Sheets: %s", e)

    logger.info("Finished processing packet")
