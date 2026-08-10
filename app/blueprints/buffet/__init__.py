from flask import Blueprint

buffet_bp = Blueprint('buffet', __name__)

from . import routes