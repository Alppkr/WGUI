from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from apscheduler.schedulers.background import BackgroundScheduler


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
scheduler = BackgroundScheduler()


def init_scheduler(app):
    """Start the background scheduler and attach it to the app."""
    if not scheduler.running:
        scheduler.start()
    app.scheduler = scheduler


