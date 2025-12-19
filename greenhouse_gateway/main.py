# greenhouse_gateway/main.py

import time
import logging
from datetime import datetime
from pathlib import Path

from .ingest import mqtt_client
from .ingest import data_collector
from .persist import storage
from .control import command_dispatcher

BASE_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "gateway.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ],
)

logger = logging.getLogger("greenhouse_gateway.main")


def main():
    logger.info("Starting Greenhouse Gateway")

    # Initialize MQTT (this starts the background loop)
    mqtt_client.init_mqtt()

    last_heartbeat = 0

    try:
        while True:
            now = time.time()

            # 1. See if any new sensor packets have arrived
            packet = mqtt_client.get_next_sensor_packet()
            if packet is not None:
                try:
                    data_collector.process_packet(packet)
                except Exception as e:
                    logger.exception("Error processing packet: %s", e)

            # 2. Check if commands.json changed and send commands if needed
            try:
                command_dispatcher.check_and_send_commands(mqtt_client.publish_command)
            except Exception as e:
                logger.exception("Error dispatching commands: %s", e)

            # 3. Send Jetson heartbeat every 10 seconds
            if now - last_heartbeat >= 10:
                try:
                    cmds = command_dispatcher.get_current_commands()
                    mqtt_client.publish_status({
                        "status": "alive",
                        "timestamp": datetime.utcnow().isoformat(),
                        "current_commands": cmds
                    })
                    last_heartbeat = now
                except Exception as e:
                    logger.exception("Error sending heartbeat: %s", e)

            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Gateway interrupted by user, shutting down")

    finally:
        mqtt_client.shutdown()
        storage.close_connection()
        logger.info("Gateway stopped")


if __name__ == "__main__":
    main()
