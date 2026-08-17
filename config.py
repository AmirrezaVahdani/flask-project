import os
import secrets


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "gym.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    LOCKER_COUNT = int(os.environ.get("LOCKER_COUNT", "3"))

    # Comma-separated origins for CORS; empty = same-origin only
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

    WTF_CSRF_ENABLED = True
