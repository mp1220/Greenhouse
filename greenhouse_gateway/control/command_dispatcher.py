# greenhouse_gateway/command_dispatcher.py

import copy
import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger("greenhouse_gateway.command_dispatcher")

# Point to project root runtime directory (greenhouse/runtime/)
BASE_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = BASE_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

COMMANDS_PATH = RUNTIME_DIR / "commands.json"

_last_sent = None  # cached copy of last sent commands
_lock = threading.Lock()  # Thread safety for _last_sent access


def _load_commands() -> dict:
    if not COMMANDS_PATH.exists():
        # Initialize with sane defaults
        default_cmds = {
            "circulation_fan_pwm": 0,
            "grow_light_pwm": 0,
            "exhaust_fan_pwm": 0
        }
        COMMANDS_PATH.write_text(json.dumps(default_cmds, indent=2))
        return default_cmds

    try:
        return json.loads(COMMANDS_PATH.read_text())
    except Exception as e:
        logger.exception("Error reading commands.json: %s", e)
        return {}


def check_and_send_commands(publish_func):
    """
    publish_func should be something like mqtt_client.publish_command(cmd_dict).
    """
    global _last_sent

    current = _load_commands()

    with _lock:
        if _last_sent is None:
            logger.info("Initial command sync, sending to ESP32: %s", current)
            publish_func(current)
            _last_sent = copy.deepcopy(current)
            return

        if current != _last_sent:
            logger.info("Commands changed, sending to ESP32: %s", current)
            publish_func(current)
            _last_sent = copy.deepcopy(current)


def get_current_commands():
    """
    Return current commands from commands.json.
    Used by heartbeat system to include current state.
    """
    return _load_commands()
