from flask import Flask
from .auth.routes import auth_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object('wgui.config.Config')

    # Security-related configs
    app.config.setdefault('SESSION_COOKIE_SECURE', True)
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')

    app.register_blueprint(auth_bp)

    return app
