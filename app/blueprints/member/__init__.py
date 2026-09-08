from flask import Blueprint

member_bp = Blueprint("member", __name__)

from . import routes  # noqa: F401,E402
