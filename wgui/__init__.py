from flask import Flask
from .auth.routes import auth_bp
from .admin import admin_bp
from .lists import lists_bp
from .extensions import db, migrate, jwt
from .error_handlers import register_error_handlers
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
    if app.config.get('TESTING'):
        app.config['JWT_COOKIE_SECURE'] = False

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

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

    register_error_handlers(app)

    if app.config.get('TESTING'):
        @app.route('/raise-validation-error')
        def raise_validation_error():
            from pydantic import BaseModel

            class Dummy(BaseModel):
                value: int

            Dummy(value='bad')

            return ''  # pragma: no cover

    return app

