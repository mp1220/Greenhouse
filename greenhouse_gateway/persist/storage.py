# greenhouse_gateway/persist/storage.py

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("greenhouse_gateway.storage")

# ------------------------------------------------------------------
# PATHS (PROJECT ROOT = greenhouse/)
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = PROJECT_ROOT / "db"
DB_PATH = DB_DIR / "greenhouse.db"
SCHEMA_PATH = PROJECT_ROOT / "greenhouse_gateway" / "persist" / "schema.sql"

DB_DIR.mkdir(parents=True, exist_ok=True)

_conn = None


def _get_connection():
    global _conn
    if _conn is None:
        logger.info("Opening SQLite database at %s", DB_PATH)
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _init_db()
    return _conn


def _init_db():
    logger.info("Initializing database schema")
    with SCHEMA_PATH.open("r") as f:
        schema_sql = f.read()
    conn = _conn
    conn.executescript(schema_sql)
    conn.commit()


def insert_sensor_reading(packet: dict):
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO samples (
            timestamp_utc,
            local_time,
            day_of_year,
            season_state,
            intent_window,

            inside_temp_f,
            inside_humidity_rh,
            inside_dew_point_f,
            inside_vpd_kpa,
            inside_brightness_lux,

            tsl_full_spectrum,
            tsl_infrared,

            outside_temp_f,
            outside_humidity_rh,
            outside_brightness_raw,
            outside_color_r,
            outside_color_g,
            outside_color_b,

            cloud_coverage_pct,
            precip_probability_pct,
            weather_code,

            expected_light_trajectory,
            expected_humidity_decay,
            forecast_confidence,

            circulation_fan_pwm,
            exhaust_fan_pwm,
            grow_light_pwm,

            disconnected_sensors,

            esp32_runtime_ms,
            firmware_version,
            wifi_rssi,
            mqtt_reconnects,

            control_mode,
            control_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            packet.get("jetson_timestamp"),
            packet.get("local_time"),
            packet.get("day_of_year"),
            packet.get("season_state"),
            packet.get("intent_window"),

            packet.get("inside_temp_f"),
            packet.get("inside_humidity_rh"),
            packet.get("inside_dew_point_f"),
            packet.get("inside_vpd_kpa"),
            packet.get("inside_brightness_lux"),

            packet.get("tsl_full_spectrum"),
            packet.get("tsl_infrared"),

            packet.get("outside_temp_f"),
            packet.get("outside_humidity_rh"),
            packet.get("outside_brightness_raw"),
            packet.get("outside_color_r"),
            packet.get("outside_color_g"),
            packet.get("outside_color_b"),

            packet.get("cloud_coverage_pct"),
            packet.get("precip_probability_pct"),
            packet.get("weather_code"),

            packet.get("expected_light_trajectory"),
            packet.get("expected_humidity_decay"),
            packet.get("forecast_confidence"),

            packet.get("circulation_fan_pwm"),
            packet.get("exhaust_fan_pwm"),
            packet.get("grow_light_pwm"),

            packet.get("disconnected_sensors"),

            packet.get("esp32_runtime_ms"),
            packet.get("firmware_version"),
            packet.get("wifi_rssi"),
            packet.get("mqtt_reconnects"),

            packet.get("control_mode"),
            packet.get("control_reason"),
        ),
    )

    conn.commit()


def close_connection():
    global _conn
    if _conn is not None:
        logger.info("Closing SQLite database connection")
        _conn.close()
        _conn = None
