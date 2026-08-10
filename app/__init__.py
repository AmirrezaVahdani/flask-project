from flask import Flask, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from app.extensions import db
from app.locker_hardware import LockerHardwareService

socketio = SocketIO()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if app.config.get("TESTING"):
        app.config["WTF_CSRF_ENABLED"] = False
    else:
        app.config.setdefault("WTF_CSRF_ENABLED", True)

    cors_origins = config_class.CORS_ORIGINS
    if cors_origins:
        CORS(app, origins=[o.strip() for o in cors_origins.split(",") if o.strip()])
    else:
        CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    app.extensions["locker_hardware"] = LockerHardwareService(app)
    socketio.init_app(
        app,
        cors_allowed_origins=cors_origins.split(",") if cors_origins else "*",
    )
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "admin.login"
    login_manager.login_message = "لطفاً ابتدا وارد حساب کاربری خود شوید."

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.sockets import PublicDashboardNamespace

    socketio.on_namespace(PublicDashboardNamespace("/public"))

    from app.blueprints.api.routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    csrf.exempt(api_bp)

    from app.blueprints.public.routes import public_bp

    app.register_blueprint(public_bp, url_prefix="/public")

    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.blueprints.buffet.routes import buffet_bp

    app.register_blueprint(buffet_bp, url_prefix="/buffet")

    @app.route("/")
    def index():
        return redirect(url_for("public.home"))

    return app
