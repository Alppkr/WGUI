from datetime import date, timedelta, datetime
import smtplib
from email.message import EmailMessage

from flask import current_app
from apscheduler.triggers.cron import CronTrigger

from .extensions import db, scheduler
from .models import DataList, EmailSettings, ScheduleSettings, AuditLog, AuditSettings, BackupSettings, ListModel, User
from .backup_utils import write_backup_file, prune_backups


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


def delete_expired_items(initiator_user_id: int | None = None) -> None:
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
            # Resolve user attribution: use initiator if provided, else system user
            user_id_for_audit = initiator_user_id
            actor_name = None
            if user_id_for_audit is None:
                sys_user = User.query.filter_by(username='system').first()
                user_id_for_audit = sys_user.id if sys_user else None
                actor_name = 'system'
            else:
                u = db.session.get(User, int(user_id_for_audit))
                actor_name = u.username if u else None
            # Preload list ids by name to avoid repeated queries
            lists = {l.name: l.id for l in ListModel.query.all()}
            # Log and delete each expired item
            for item in expired:
                list_id = lists.get(item.category)
                db.session.add(
                    AuditLog(
                        user_id=user_id_for_audit,
                        actor_name=actor_name,
                        action='item_deleted',
                        target_type='item',
                        target_id=item.id,
                        list_id=list_id,
                        details=f"category={item.category}; data={item.data}; reason=expired",
                    )
                )
                db.session.delete(item)
            db.session.commit()


def _job(app):
    with app.app_context():
        delete_expired_items(initiator_user_id=None)
        # Audit: scheduled job run
        try:
            db.session.add(
                AuditLog(
                    user_id=None,
                    actor_name='system',
                    action='cleanup_job_run',
                    target_type='job',
                    target_id=None,
                    details='trigger=schedule',
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()


def update_cleanup_schedule(app) -> None:
    """(Re)register the cleanup job according to DB settings."""
    with app.app_context():
        settings = ScheduleSettings.query.first()
        hour = settings.hour if settings else 0
        minute = settings.minute if settings else 0
    # Replace existing job with id 'cleanup_job'
    scheduler.add_job(lambda: _job(app), CronTrigger(hour=hour, minute=minute), id='cleanup_job', replace_existing=True)


def run_backup_task(app) -> None:
    with app.app_context():
        try:
            # Use DB-configured backup settings if present
            bdir = None
            bkeep = None
            cfg = BackupSettings.query.first()
            if cfg:
                bdir = cfg.directory
                bkeep = cfg.keep
            path = write_backup_file(app, directory=bdir)
            db.session.add(
                AuditLog(
                    user_id=None,
                    actor_name='system',
                    action='backup_created',
                    target_type='backup',
                    target_id=None,
                    details=f"path={path}; trigger=schedule",
                )
            )
            db.session.commit()
            prune_backups(app, directory=bdir, keep=bkeep)
        except Exception:
            db.session.rollback()


def run_audit_purge_task(app) -> None:
    with app.app_context():
        # purge old audit logs based on retention
        try:
            cfg = AuditSettings.query.first()
            days = int(cfg.retention_days) if cfg else 90
            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted = (db.session.query(AuditLog)
                .filter(AuditLog.created_at < cutoff)
                .delete(synchronize_session=False))
            db.session.commit()
            # optional: audit a purge run row (no sensitive details)
            db.session.add(
                AuditLog(
                    user_id=None,
                    actor_name='system',
                    action='audit_purge_run',
                    target_type='audit',
                    target_id=None,
                    details=f"removed={deleted}",
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()


def update_backup_schedule(app) -> None:
    with app.app_context():
        settings = ScheduleSettings.query.first()
        hour = settings.backup_hour if settings else 0
        minute = settings.backup_minute if settings else 0
    scheduler.add_job(lambda: run_backup_task(app), CronTrigger(hour=hour, minute=minute), id='backup_job', replace_existing=True)


def update_audit_purge_schedule(app) -> None:
    with app.app_context():
        settings = ScheduleSettings.query.first()
        hour = settings.audit_hour if settings else 0
        minute = settings.audit_minute if settings else 0
    scheduler.add_job(lambda: run_audit_purge_task(app), CronTrigger(hour=hour, minute=minute), id='audit_purge_job', replace_existing=True)


def schedule_tasks(app) -> None:
    """Register scheduled jobs at startup."""
    update_cleanup_schedule(app)
    update_backup_schedule(app)
    update_audit_purge_schedule(app)
