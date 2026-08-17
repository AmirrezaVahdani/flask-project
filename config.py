import os
import secrets
from dotenv import load_dotenv

# لود کردن متغیرها از فایل .env در ریشه پروژه
load_dotenv()


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "gym.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    LOCKER_COUNT = int(os.environ.get("LOCKER_COUNT", "3"))

    # تنظیمات سخت‌افزار کمدها
    LOCKER_HARDWARE_MODE = os.environ.get("LOCKER_HARDWARE_MODE", "gpio")
    LOCKER_OPEN_DURATION_SECONDS = int(os.environ.get("LOCKER_OPEN_DURATION_SECONDS", "30"))
    LOCKER_HARDWARE_GPIO_PIN_MAP = os.environ.get("LOCKER_HARDWARE_GPIO_PIN_MAP", "1:17,2:27,3:22")
    LOCKER_HARDWARE_GPIO_ACTIVE_STATE = int(os.environ.get("LOCKER_HARDWARE_GPIO_ACTIVE_STATE", "1"))
    LOCKER_HARDWARE_OPEN_COMMAND = os.environ.get("LOCKER_HARDWARE_OPEN_COMMAND", "")
    LOCKER_HARDWARE_CLOSE_COMMAND = os.environ.get("LOCKER_HARDWARE_CLOSE_COMMAND", "")
    LOCKER_HARDWARE_GPIO_OPEN_PIN = os.environ.get("LOCKER_HARDWARE_GPIO_OPEN_PIN", "")
    LOCKER_HARDWARE_GPIO_CLOSE_PIN = os.environ.get("LOCKER_HARDWARE_GPIO_CLOSE_PIN", "")

    # Comma-separated origins for CORS; empty = same-origin only
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

    WTF_CSRF_ENABLED = True
