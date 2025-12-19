# greenhouse_gateway/google_sheets.py

import json
import logging
import time
from datetime import datetime, date
from pathlib import Path
from statistics import mode, StatisticsError
from typing import Optional

import requests
from dotenv import load_dotenv
import os

logger = logging.getLogger("greenhouse_gateway.google_sheets")

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / "config" / ".env"
CONFIG_PATH = BASE_DIR / "config" / "config.json"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

GOOGLE_SHEETS_ENDPOINT = os.getenv("GOOGLE_SHEETS_ENDPOINT", "")

# Load config
_config = {}
if CONFIG_PATH.exists():
    try:
        _config = json.loads(CONFIG_PATH.read_text())
    except Exception as e:
        logger.exception("Error loading config.json: %s", e)

UPLOAD_INTERVAL = _config.get("sheets_upload_interval_seconds", 300)
AVERAGING_FIELDS = _config.get("averaging_fields", [])

MODE_FIELDS = _config.get("mode_fields", [])

# Buffer state
_buffer = []
_last_upload = 0.0
_first_packet_sent = False

# Summary state
_last_summary_date: Optional[str] = None


# ============================================================
# RAW SAMPLE HANDLING
# ============================================================

def add_packet(packet: dict) -> None:
    """
    Buffer incoming sample packets and upload averaged data
    to Google Sheets at a fixed interval.
    """
    global _last_upload, _buffer, _first_packet_sent

    now = time.time()

    # First packet is sent immediately
    if not _first_packet_sent:
        logger.info("Sending first RAW packet immediately to Google Sheets")
        result = dict(packet)
        result["timestamp"] = datetime.utcnow().isoformat()
        result["type"] = "sample"
        result["sample_count"] = 1
        _send_to_sheets(result)
        _first_packet_sent = True
        _last_upload = now
        return

    _buffer.append(packet)

    if now - _last_upload < UPLOAD_INTERVAL:
        return

    averaged = _compute_average(_buffer)
    _buffer = []
    _last_upload = now

    if averaged:
        averaged["type"] = "sample"
        _send_to_sheets(averaged)


def _compute_average(packets: list[dict]) -> dict:
    if not packets:
        return {}

    result: dict = {}

    # Average numeric fields
    for field in AVERAGING_FIELDS:
        values = [
            p.get(field) for p in packets
            if isinstance(p.get(field), (int, float))
        ]
        if values:
            result[field] = sum(values) / len(values)

    # Mode fields (PWM, intent, etc)
    for field in MODE_FIELDS:
        values = [p.get(field) for p in packets if field in p]
        if values:
            try:
                result[field] = mode(values)
            except StatisticsError:
                result[field] = values[-1]

    # Pass-through fields (latest value) - for Google Sheets
    passthrough_fields = [
        "local_time",              # Timestamp for sheets
        "outside_brightness_raw",  # Weather data
        "cloud_coverage_pct",
        "intent_window",           # Time context
        "control_mode",            # Control context
        "control_reason"
    ]
    for field in passthrough_fields:
        values = [p.get(field) for p in packets if field in p]
        if values:
            result[field] = values[-1]  # Latest value

    result["timestamp"] = datetime.utcnow().isoformat()
    result["sample_count"] = len(packets)
    return result


# ============================================================
# DAILY SUMMARY HANDLING
# ============================================================

def upload_daily_summary(summary_payload: dict) -> None:
    """
    Upload a precomputed daily summary payload to Google Sheets.

    summary_payload MUST already include:
      - type: "summary"
      - date: YYYY-MM-DD
      - all summary fields computed on Jetson
    """
    global _last_summary_date

    day = summary_payload.get("date")
    if not day:
        logger.warning("Summary payload missing date, skipping")
        return

    if _last_summary_date == day:
        logger.info("Daily summary for %s already sent, skipping", day)
        return

    logger.info("Uploading daily summary for %s to Google Sheets", day)
    _send_to_sheets(summary_payload)
    _last_summary_date = day


# ============================================================
# LOW-LEVEL UPLOAD
# ============================================================

def _send_to_sheets(packet: dict) -> None:
    """
    POST a packet (sample or summary) to the Google Sheets endpoint.
    Renames fields for sample packets to match Google Sheets script expectations.
    """
    if not GOOGLE_SHEETS_ENDPOINT:
        logger.warning("GOOGLE_SHEETS_ENDPOINT not set, skipping upload")
        return

    # Rename fields for sample packets to match Google Sheets script
    payload = dict(packet)
    if packet.get("type") == "sample":
        # Create renamed payload with only the fields Google Sheets expects
        payload = {
            "type": "sample",
            "local_time": packet.get("local_time"),
            "inside_temp_f": packet.get("temperature_f"),
            "inside_humidity_rh": packet.get("humidity_rh"),
            "inside_brightness_lux": packet.get("lux"),
            "outside_brightness_raw": packet.get("outside_brightness_raw"),
            "cloud_coverage_pct": packet.get("cloud_coverage_pct"),
            "circulation_fan_pwm": packet.get("circulator_fan_pwm"),
            "exhaust_fan_pwm": packet.get("exhaust_fan_pwm"),
            "grow_light_pwm": packet.get("light_pwm"),
            "intent_window": packet.get("intent_window"),
            "control_mode": packet.get("control_mode"),
            "control_reason": packet.get("control_reason"),
        }

    try:
        resp = requests.post(
            GOOGLE_SHEETS_ENDPOINT,
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning(
                "Sheets upload returned %s: %s",
                resp.status_code,
                resp.text[:200],
            )
        else:
            logger.info(
                "Successfully uploaded %s packet to Google Sheets",
                packet.get("type", "unknown"),
            )

    except Exception as e:
        logger.exception("Error uploading to Google Sheets: %s", e)
