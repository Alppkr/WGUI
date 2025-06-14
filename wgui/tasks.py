from datetime import date
from celery.schedules import crontab

from .extensions import celery, db
from .models import DataList


@celery.task
def delete_expired_items():
    """Delete list items whose date is before today."""
    app = celery.flask_app
    with app.app_context():
        today = date.today()
        expired = DataList.query.filter(DataList.date < today).all()
        for item in expired:
            db.session.delete(item)
        if expired:
            db.session.commit()


# schedule the task daily at midnight
celery.conf.beat_schedule = {
    "delete-expired-items-daily": {
        "task": "wgui.tasks.delete_expired_items",
        "schedule": crontab(hour=0, minute=0),
    }
}

