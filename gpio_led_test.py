import os
import time


try:
    import RPi.GPIO as GPIO
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"RPi.GPIO not available: {exc}")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pin_map = {
    1: int(os.environ.get("LOCKER_GPIO_PIN_1", "17")),
    2: int(os.environ.get("LOCKER_GPIO_PIN_2", "27")),
    3: int(os.environ.get("LOCKER_GPIO_PIN_3", "22")),
    4: int(os.environ.get("LOCKER_GPIO_PIN_4", "23")),
}

for pin in pin_map.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

print("GPIO test started. LEDs are OFF. Press Ctrl+C to exit.")
try:
    while True:
        for locker_number, pin in pin_map.items():
            GPIO.output(pin, GPIO.HIGH)
            print(f"Locker {locker_number}: LED ON")
            time.sleep(0.5)
            GPIO.output(pin, GPIO.LOW)
            time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    for pin in pin_map.values():
        GPIO.output(pin, GPIO.LOW)
    GPIO.cleanup()
