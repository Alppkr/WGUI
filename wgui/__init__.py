from flask import Flask
from .auth.routes import auth_bp
from .admin import admin_bp
from .lists import lists_bp
from .extensions import db, migrate
from flask_migrate import upgrade
from .models import User, ListModel
import os


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object('wgui.config.Config')
    if config_overrides:
        app.config.update(config_overrides)

    # Security-related configs
    app.config.setdefault('SESSION_COOKIE_SECURE', True)
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///:memory:'):
            db.create_all()
        else:
            upgrade()
        if not User.query.filter_by(username=app.config['USERNAME']).first():
            user = User(
                username=app.config['USERNAME'],
                email='admin@example.com',
                hashed_password=app.config['PASSWORD_HASH'],
                is_admin=True,
                first_login=True,
            )
            db.session.add(user)
        db.session.commit()


    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(lists_bp)

    return app
