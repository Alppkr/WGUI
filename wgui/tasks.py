from datetime import date, timedelta
import smtplib
from email.message import EmailMessage

from flask import current_app
from apscheduler.triggers.cron import CronTrigger

from .extensions import db, scheduler
from .models import DataList, EmailSettings


def send_email(subject: str, body: str) -> None:
    """Send an email using settings stored in the database."""
    app = current_app._get_current_object()
    with app.app_context():
        settings = EmailSettings.query.first()
        if not settings:
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.from_email

        recipients = [r.strip() for r in settings.to_email.split(',') if r.strip()]
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as smtp:
                if settings.smtp_user or settings.smtp_pass:
                    smtp.login(settings.smtp_user, settings.smtp_pass)
                smtp.send_message(msg, to_addrs=recipients)

        except Exception:
            pass


def delete_expired_items() -> None:
    """Delete expired items and notify about upcoming removals."""
    app = current_app._get_current_object()
    with app.app_context():
        today = date.today()

        # notify upcoming expirations with a single email
        upcoming_map: dict[int, list[DataList]] = {}
        for days in (30, 15, 7, 3, 1):
            target = today + timedelta(days=days)
            items = DataList.query.filter(DataList.date == target).all()
            if items:
                upcoming_map[days] = items

        if upcoming_map:
            parts: list[str] = []
            for days, items in sorted(upcoming_map.items()):
                lines = [f"{item.category}: {item.data}" for item in items]
                parts.append(f"In {days} days:\n" + "\n".join(lines))
            body = "The following entries will expire soon:\n\n" + "\n\n".join(parts)
            send_email("Entries expiring soon", body)


        # delete expired items
        expired = DataList.query.filter(DataList.date < today).all()
        if expired:
            lines = [f"{item.category}: {item.data}" for item in expired]
            body = "The following entries were removed:\n" + "\n".join(lines)
            send_email("Entries removed", body)
            for item in expired:
                db.session.delete(item)
            db.session.commit()


def schedule_tasks(app) -> None:
    """Register scheduled jobs."""

    def run_job():
        with app.app_context():
            delete_expired_items()

    scheduler.add_job(run_job, CronTrigger(hour=0, minute=0))
