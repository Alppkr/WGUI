from datetime import date, timedelta
import smtplib
from email.message import EmailMessage
from celery.schedules import crontab

from .extensions import celery, db
from .models import DataList, EmailSettings


def send_email(subject: str, body: str) -> None:
    """Send an email using settings stored in the database."""
    app = celery.flask_app
    with app.app_context():
        settings = EmailSettings.query.first()
        if not settings:
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.from_email
        msg["To"] = settings.to_email
        msg.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as smtp:
                if settings.smtp_user or settings.smtp_pass:
                    smtp.login(settings.smtp_user, settings.smtp_pass)
                smtp.send_message(msg)
        except Exception:
            pass


@celery.task
def delete_expired_items():
    """Delete expired items and notify about upcoming removals."""
    app = celery.flask_app
    with app.app_context():
        today = date.today()

        # notify upcoming expirations
        for days in (30, 15, 7, 3, 1):
            target = today + timedelta(days=days)
            upcoming = DataList.query.filter(DataList.date == target).all()
            if upcoming:
                lines = [f"{item.category}: {item.data}" for item in upcoming]
                body = (
                    f"The following entries will be removed in {days} days:\n" + "\n".join(lines)
                )
                send_email(
                    f"Entries expiring in {days} days",
                    body,
                )

        # delete expired items
        expired = DataList.query.filter(DataList.date < today).all()
        if expired:
            lines = [f"{item.category}: {item.data}" for item in expired]
            body = "The following entries were removed:\n" + "\n".join(lines)
            send_email("Entries removed", body)
            for item in expired:
                db.session.delete(item)
            db.session.commit()


# schedule the task daily at midnight
celery.conf.beat_schedule = {
    "delete-expired-items-daily": {
        "task": "wgui.tasks.delete_expired_items",
        "schedule": crontab(hour=0, minute=0),
    }
}

