# greenhouse_gateway/mqtt_client.py

import json
import logging
import queue
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os

logger = logging.getLogger("greenhouse_gateway.mqtt")

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / "config" / ".env"

# Load env variables
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

SENSOR_TOPIC = os.getenv("MQTT_SENSOR_TOPIC", "greenhouse/sensors")
COMMAND_TOPIC = os.getenv("MQTT_COMMAND_TOPIC", "greenhouse/commands")
STATUS_TOPIC = os.getenv("MQTT_STATUS_TOPIC", "greenhouse/jetson/status")

# Internal state
_client = None
_sensor_queue: "queue.Queue[dict]" = queue.Queue(maxsize=100)


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        logger.info("Connected to MQTT broker at %s:%s", MQTT_BROKER, MQTT_PORT)
        client.subscribe(SENSOR_TOPIC)
        logger.info("Subscribed to sensor topic: %s", SENSOR_TOPIC)
    else:
        logger.error("Failed to connect to MQTT broker: %s", reason_code)


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        logger.debug("Received MQTT message on %s: %s", msg.topic, data)

        if msg.topic == SENSOR_TOPIC:
            try:
                _sensor_queue.put_nowait(data)
            except queue.Full:
                logger.warning("Sensor queue full, dropping packet")

    except Exception as e:
        logger.exception("Error handling MQTT message: %s", e)


def init_mqtt():
    global _client

    logger.info("Initializing MQTT client")

    _client = mqtt.Client()

    if MQTT_USERNAME:
        _client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD or None)

    _client.on_connect = on_connect
    _client.on_message = on_message

    # Retry connection with exponential backoff
    retry_delay = 1
    max_delay = 60

    while True:
        try:
            logger.info("Attempting to connect to MQTT broker at %s:%s", MQTT_BROKER, MQTT_PORT)
            _client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            _client.loop_start()
            logger.info("MQTT client initialized successfully")
            break
        except Exception as e:
            logger.error("Failed to connect to MQTT broker: %s. Retrying in %d seconds...", e, retry_delay)
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)  # Exponential backoff


def get_next_sensor_packet():
    """Non blocking: returns next packet dict or None if none waiting."""
    try:
        return _sensor_queue.get_nowait()
    except queue.Empty:
        return None


def publish_command(cmd: dict):
    """Publish command dict to ESP32."""
    if _client is None:
        logger.error("MQTT client not initialized, cannot publish")
        return

    try:
        payload = json.dumps(cmd)
        logger.info("Publishing command to %s: %s", COMMAND_TOPIC, payload)
        _client.publish(COMMAND_TOPIC, payload, qos=1)
    except Exception as e:
        logger.exception("Error publishing command: %s", e)


def publish_status(payload: dict):
    """Publish Jetson heartbeat/status message."""
    if _client is None:
        logger.error("MQTT client not initialized, cannot publish status")
        return

    try:
        payload_json = json.dumps(payload)
        logger.debug("Publishing status to %s", STATUS_TOPIC)
        _client.publish(STATUS_TOPIC, payload_json, qos=0)
    except Exception as e:
        logger.exception("Error publishing heartbeat/status: %s", e)


def shutdown():
    global _client
    if _client is not None:
        logger.info("Stopping MQTT loop")
        _client.loop_stop()
        _client.disconnect()
        _client = None
