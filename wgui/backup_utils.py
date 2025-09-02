import os
import json
from datetime import datetime
from typing import Optional

from .extensions import db
from .models import User, ListModel, DataList, EmailSettings, ScheduleSettings, AuditLog, AuditSettings, BackupSettings


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def build_backup_payload(app) -> dict:
    """Collect all data into a backup payload dict.

    Structure is compatible with admin backup download/restore.
    """
    with app.app_context():
        users = [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'hashed_password': u.hashed_password,
                'is_admin': bool(u.is_admin),
                'first_login': bool(u.first_login),
            }
            for u in User.query.order_by(User.id.asc()).all()
        ]
        lists = [
            {
                'id': l.id,
                'name': l.name,
                'type': l.type,
            }
            for l in ListModel.query.order_by(ListModel.id.asc()).all()
        ]
        items = [
            {
                'id': i.id,
                'category': i.category,
                'data': i.data,
                'description': i.description,
                'date': i.date.isoformat() if hasattr(i.date, 'isoformat') else str(i.date),
                'creator_id': i.creator_id,
            }
            for i in DataList.query.order_by(DataList.id.asc()).all()
        ]
        es = EmailSettings.query.first()
        email_settings: Optional[dict] = None
        if es:
            email_settings = {
                'id': es.id,
                'from_email': es.from_email,
                'to_email': es.to_email,
                'smtp_server': es.smtp_server,
                'smtp_port': es.smtp_port,
                'smtp_user': es.smtp_user or '',
                'smtp_pass': es.smtp_pass or '',
            }
        ss = ScheduleSettings.query.first()
        schedule_settings: Optional[dict] = None
        if ss:
            schedule_settings = {
                'id': ss.id,
                'hour': ss.hour,
                'minute': ss.minute,
                'backup_hour': ss.backup_hour,
                'backup_minute': ss.backup_minute,
                'audit_hour': ss.audit_hour,
                'audit_minute': ss.audit_minute,
            }
        aus = AuditSettings.query.first()
        audit_settings: Optional[dict] = None
        if aus:
            audit_settings = {
                'id': aus.id,
                'retention_days': aus.retention_days,
            }
        audits = [
            {
                'id': a.id,
                'created_at': a.created_at.isoformat() if hasattr(a.created_at, 'isoformat') else str(a.created_at),
                'user_id': a.user_id,
                'action': a.action,
                'target_type': a.target_type,
                'target_id': a.target_id,
                'list_id': a.list_id,
                'details': a.details,
            }
            for a in AuditLog.query.order_by(AuditLog.id.asc()).all()
        ]
        bks = BackupSettings.query.first()
        backup_settings = None
        if bks:
            # Do not include directory in exported payload; export only keep count
            backup_settings = {
                'keep': bks.keep,
            }

        return {
            'version': 1,
            'created_at': _now_iso(),
            'users': users,
            'lists': lists,
            'items': items,
            'email_settings': email_settings,
            'schedule_settings': schedule_settings,
            'audit_settings': audit_settings,
            'audits': audits,
            'backup_settings': backup_settings,
        }


def ensure_backup_dir(app, directory: str | None = None) -> str:
    path = directory or app.config.get('BACKUP_DIR') or os.path.join(app.instance_path, 'backups')
    os.makedirs(path, exist_ok=True)
    return path


def write_backup_file(app, directory: str | None = None) -> str:
    """Write a backup JSON file to BACKUP_DIR and return its path."""
    payload = build_backup_payload(app)
    data = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    d = ensure_backup_dir(app, directory)
    fname = f"wgui-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    path = os.path.join(d, fname)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(data)
    return path


def prune_backups(app, directory: str | None = None, keep: int | None = None) -> list[str]:
    """Keep only the latest BACKUP_KEEP files. Return list of deleted paths."""
    d = ensure_backup_dir(app, directory)
    keep = int(keep if keep is not None else app.config.get('BACKUP_KEEP', 3))
    entries = [
        os.path.join(d, fn)
        for fn in os.listdir(d)
        if fn.startswith('wgui-backup-') and fn.endswith('.json') and os.path.isfile(os.path.join(d, fn))
    ]
    # sort by filename timestamp descending
    entries.sort(reverse=True)
    to_delete = entries[keep:] if len(entries) > keep else []
    deleted = []
    for p in to_delete:
        try:
            os.remove(p)
            deleted.append(p)
        except Exception:
            pass
    return deleted


def get_latest_backup(app, directory: str | None = None):
    """Return a tuple (path, mtime_datetime) for the newest backup, or (None, None)."""
    d = ensure_backup_dir(app, directory)
    entries = [
        os.path.join(d, fn)
        for fn in os.listdir(d)
        if fn.startswith('wgui-backup-') and fn.endswith('.json') and os.path.isfile(os.path.join(d, fn))
    ]
    if not entries:
        return None, None
    latest = max(entries, key=lambda p: os.path.getmtime(p))
    ts = os.path.getmtime(latest)
    return latest, datetime.utcfromtimestamp(ts)
