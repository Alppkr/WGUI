from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from celery import Celery


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
celery = Celery('wgui')


def init_celery(app):
    """Configure Celery with the Flask app context."""
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND'),
    )
    celery.flask_app = app



