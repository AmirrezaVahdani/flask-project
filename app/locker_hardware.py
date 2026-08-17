import logging
import os
import subprocess
import threading
from typing import Dict, Optional

from flask import current_app

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except Exception:
    GPIO = None
    GPIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class LockerHardwareService:
    def __init__(self, app=None):
        self.app = app
        self.mode = self._get_config("LOCKER_HARDWARE_MODE", "mock")
        self.open_duration_seconds = int(
            self._get_config("LOCKER_OPEN_DURATION_SECONDS", "30")
        )
        self.open_command = self._get_config("LOCKER_HARDWARE_OPEN_COMMAND", "")
        self.close_command = self._get_config("LOCKER_HARDWARE_CLOSE_COMMAND", "")
        self.gpio_open_pin = self._parse_int(self._get_config("LOCKER_HARDWARE_GPIO_OPEN_PIN", ""))
        self.gpio_close_pin = self._parse_int(self._get_config("LOCKER_HARDWARE_GPIO_CLOSE_PIN", ""))
        self.gpio_pin_map = self._parse_gpio_pin_map(
            self._get_config("LOCKER_HARDWARE_GPIO_PIN_MAP", "")
        )
        self.gpio_active_state = int(self._get_config("LOCKER_HARDWARE_GPIO_ACTIVE_STATE", "1"))
        self._timers: Dict[int, threading.Timer] = {}
        self._timer_lock = threading.Lock()
        self._init_gpio()

    def _init_gpio(self) -> None:
        if self.mode != "gpio" or not GPIO_AVAILABLE:
            if self.mode == "gpio" and not GPIO_AVAILABLE:
                logger.warning("LOCKER_HARDWARE_MODE is gpio but RPi.GPIO is not available")
            return
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            for pin in set(self.gpio_pin_map.values()):
                GPIO.setup(int(pin), GPIO.OUT)
                GPIO.output(int(pin), 0 if self.gpio_active_state == 1 else 1)
            logger.info("GPIO initialized for pins: %s", self.gpio_pin_map)
        except Exception as exc:
            logger.error("GPIO init failed: %s", exc)

    def _get_config(self, key, default):
        if self.app is not None:
            value = self.app.config.get(key, None)
            if value is not None:
                return value
        return os.environ.get(key, default)

    def _parse_int(self, value: str) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return None

    def _parse_gpio_pin_map(self, value: str) -> Dict[int, int]:
        pin_map: Dict[int, int] = {}
        if not value:
            return pin_map
        for item in str(value).split(","):
            item = item.strip()
            if not item or ":" not in item:
                continue
            locker_str, pin_str = item.split(":", 1)
            try:
                locker = int(locker_str.strip())
                pin = int(pin_str.strip())
            except ValueError:
                continue
            pin_map[locker] = pin
        return pin_map

    def _get_gpio_pin(self, locker_number: int, open_state: bool) -> Optional[int]:
        if locker_number in self.gpio_pin_map:
            return self.gpio_pin_map[locker_number]
        if open_state:
            return self.gpio_open_pin
        return self.gpio_close_pin if self.gpio_close_pin is not None else self.gpio_open_pin

    def open_locker(self, locker_number: int) -> Dict[str, object]:
        if self.mode == "mock":
            logger.info("Mock locker hardware: opening locker %s", locker_number)
            self._schedule_close(locker_number)
            return {
                "opened": True,
                "duration": self.open_duration_seconds,
                "mode": self.mode,
                "locker_number": locker_number,
            }
        if self.mode in {"command", "shell"}:
            result = self._run_command(self.open_command, locker_number, "open")
            if result["ok"]:
                self._schedule_close(locker_number)
            return {
                "opened": result["ok"],
                "duration": self.open_duration_seconds,
                "mode": self.mode,
                "locker_number": locker_number,
                "error": result.get("error"),
            }
        if self.mode == "gpio":
            result = self._run_gpio(locker_number, open_state=True)
            if result["ok"]:
                self._schedule_close(locker_number)
            return {
                "opened": result["ok"],
                "duration": self.open_duration_seconds,
                "mode": self.mode,
                "locker_number": locker_number,
                "error": result.get("error"),
            }
        raise ValueError(f"Unsupported locker hardware mode: {self.mode}")

    def close_locker(self, locker_number: int) -> Dict[str, object]:
        if self.mode == "mock":
            logger.info("Mock locker hardware: closing locker %s", locker_number)
            return {"closed": True, "locker_number": locker_number, "mode": self.mode}
        if self.mode in {"command", "shell"}:
            result = self._run_command(self.close_command, locker_number, "close")
            return {
                "closed": result["ok"],
                "locker_number": locker_number,
                "mode": self.mode,
                "error": result.get("error"),
            }
        if self.mode == "gpio":
            result = self._run_gpio(locker_number, open_state=False)
            return {
                "closed": result["ok"],
                "locker_number": locker_number,
                "mode": self.mode,
                "error": result.get("error"),
            }
        return {"closed": False, "locker_number": locker_number, "mode": self.mode}

    def _schedule_close(self, locker_number: int) -> None:
        with self._timer_lock:
            previous = self._timers.get(locker_number)
            if previous is not None:
                previous.cancel()
            timer = threading.Timer(
                self.open_duration_seconds,
                lambda: self.close_locker(locker_number),
            )
            timer.daemon = True
            timer.start()
            self._timers[locker_number] = timer

    def _run_command(self, command_template: str, locker_number: int, action: str):
        if not command_template:
            logger.warning("No command template provided for locker %s %s action", locker_number, action)
            return {"ok": True, "error": None}
        command = command_template.format(locker_number=locker_number, action=action)
        try:
            completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            if completed.returncode != 0:
                return {"ok": False, "error": completed.stderr or completed.stdout}
            return {"ok": True, "error": None}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_gpio(self, locker_number: int, open_state: bool):
        pin = self._get_gpio_pin(locker_number, open_state)
        if pin is None:
            return {"ok": True, "error": None}
        if not GPIO_AVAILABLE:
            return {"ok": False, "error": "RPi.GPIO not available"}
        try:
            GPIO.output(
                int(pin),
                self.gpio_active_state if open_state else (0 if self.gpio_active_state == 1 else 1),
            )
            return {"ok": True, "error": None}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

def get_locker_hardware_service() -> LockerHardwareService:
    service = current_app.extensions.get("locker_hardware")
    if service is None:
        service = LockerHardwareService(current_app)
        current_app.extensions["locker_hardware"] = service
    return service
