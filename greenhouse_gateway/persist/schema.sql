-- greenhouse_gateway/schema.sql
-- Hardened schema for greenhouse time-series logging
-- Design principles:
--   - NULL for missing/failed sensor readings (never 0)
--   - One row per timestamped sample
--   - Actuator state = PWM only (0 = off, no boolean flags)
--   - AI-ready: stable, explicit, no redundant fields

-- ============================================================================
-- TABLE: samples
-- ============================================================================
-- Core time-series table: one row per sensor sample
-- All fields except timestamp_utc are nullable to handle sensor failures
-- gracefully without blocking data insertion

CREATE TABLE IF NOT EXISTS samples (
    -- Primary key: UTC timestamp
    timestamp_utc TEXT PRIMARY KEY NOT NULL,

    -- Time context
    local_time TEXT,
    day_of_year INTEGER,

    -- Environmental context
    season_state TEXT,
    intent_window TEXT,

    -- ========================================================================
    -- INSIDE PRIMARY SENSOR DATA (nullable)
    -- ========================================================================
    inside_temp_f REAL,
    inside_humidity_rh REAL,
    inside_dew_point_f REAL,
    inside_vpd_kpa REAL,
    inside_brightness_lux REAL,

    -- ========================================================================
    -- LIGHT SPECTRUM DATA (ESP32 - for ML training)
    -- ========================================================================
    tsl_full_spectrum INTEGER,          -- TSL2591 full spectrum raw value
    tsl_infrared INTEGER,               -- TSL2591 infrared raw value

    -- ========================================================================
    -- OUTSIDE METADATA (nullable)
    -- ========================================================================
    outside_temp_f REAL,
    outside_humidity_rh REAL,
    outside_brightness_raw REAL,
    outside_color_r INTEGER,
    outside_color_g INTEGER,
    outside_color_b INTEGER,
    cloud_coverage_pct REAL,
    precip_probability_pct REAL,
    weather_code TEXT,

    -- ========================================================================
    -- DERIVED FIELDS (non-ML, explainable)
    -- ========================================================================
    expected_light_trajectory TEXT,
    expected_humidity_decay TEXT,
    forecast_confidence REAL,

    -- ========================================================================
    -- ACTUATORS (numeric PWM state only, 0 = off)
    -- ========================================================================
    circulation_fan_pwm INTEGER,
    exhaust_fan_pwm INTEGER,
    grow_light_pwm INTEGER,

    -- ========================================================================
    -- SENSOR CONNECTIVITY (metadata)
    -- ========================================================================
    disconnected_sensors TEXT,

    -- ========================================================================
    -- SYSTEM HEALTH (ESP32 diagnostics for ML/debugging)
    -- ========================================================================
    esp32_runtime_ms INTEGER,           -- ESP32 uptime in milliseconds
    firmware_version TEXT,              -- ESP32 firmware version string
    wifi_rssi INTEGER,                  -- WiFi signal strength (dBm, negative)
    mqtt_reconnects INTEGER,            -- MQTT reconnection count

    -- ========================================================================
    -- CONTROL CONTEXT
    -- ========================================================================
    control_mode TEXT,
    control_reason TEXT
);

-- Index for time-range queries
CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON samples(timestamp_utc);

-- Index for day-of-year analysis
CREATE INDEX IF NOT EXISTS idx_samples_day_of_year ON samples(day_of_year);


-- ============================================================================
-- TABLE: daily_summary
-- ============================================================================
-- Daily aggregated statistics generated once per day
-- Should not be continuously updated during the day

CREATE TABLE IF NOT EXISTS daily_summary (
    -- Primary key: date (YYYY-MM-DD)
    date TEXT PRIMARY KEY NOT NULL,

    -- Context
    season_state TEXT,

    -- Temperature statistics
    avg_temp_f REAL,
    min_temp_f REAL,
    max_temp_f REAL,

    -- Humidity statistics
    avg_humidity_rh REAL,
    min_humidity_rh REAL,
    max_humidity_rh REAL,

    -- Actuator runtime (in minutes)
    total_light_minutes INTEGER,
    total_exhaust_minutes INTEGER,
    total_circulation_minutes INTEGER,

    -- Human notes
    notes TEXT
);

-- Index for season analysis
CREATE INDEX IF NOT EXISTS idx_daily_summary_season ON daily_summary(season_state);
