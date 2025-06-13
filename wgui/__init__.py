from flask import Flask
from .auth.routes import auth_bp
from .admin import admin_bp
from .lists import lists_bp
from .extensions import db, migrate
from .models import User, ListModel
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object('wgui.config.Config')

    # Security-related configs
    app.config.setdefault('SESSION_COOKIE_SECURE', True)
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')

    db.init_app(app)
    migrate.init_app(app, db)

    if not os.environ.get('FLASK_MIGRATE'):
        with app.app_context():
            db.create_all()
            if not User.query.filter_by(username=app.config['USERNAME']).first():
                user = User(
                    username=app.config['USERNAME'],
                    email='admin@example.com',
                    hashed_password=app.config['PASSWORD_HASH'],
                    is_admin=True,
                    first_login=True,
                )
                db.session.add(user)
            # seed default lists if none exist
            if ListModel.query.count() == 0:
                for name in ['Ip', 'Ip Range', 'String']:
                    db.session.add(ListModel(name=name))
            db.session.commit()


    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(lists_bp)

    return app
