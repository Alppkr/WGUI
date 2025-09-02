from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
    Response,
)
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from werkzeug.security import generate_password_hash

from ..models import (
    User,
    EmailSettings,
    ScheduleSettings,
    AuditLog,
    ListModel,
    DataList,
    AuditSettings,
    BackupSettings,
)
from ..extensions import db
from .forms import (
    AddUserForm,
    DeleteForm,
    EmailSettingsForm,
    ScheduleSettingsForm,
    CleanupScheduleForm,
    BackupScheduleForm,
    AuditScheduleForm,
    BackupDownloadForm,
    BackupRestoreForm,
)
from .models import AddUserData, EmailSettingsData
from ..tasks import update_cleanup_schedule, update_backup_schedule
from flask import current_app
from datetime import datetime, timedelta
import os
import json
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
from ..backup_utils import build_backup_payload, write_backup_file, prune_backups, get_latest_backup

admin_bp = Blueprint('users', __name__, url_prefix='/users')


def admin_required():
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        return claims.get('is_admin') is True
    except Exception:
        return False


@admin_bp.before_request
def check_admin():
    if not admin_required():
        return redirect(url_for('auth.login'))


@admin_bp.route('/')
def list_users():
    users = User.query.all()
    delete_form = DeleteForm()
    return render_template('user_list.html', users=users, delete_form=delete_form)


@admin_bp.route('/add', methods=['GET', 'POST'])
def add_user():
    form = AddUserForm()
    if form.validate_on_submit():
        data = AddUserData(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
        )
        if User.query.filter_by(username=data.username).first():
            flash('User already exists', 'danger')
            return redirect(url_for('users.add_user'))
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=generate_password_hash(data.password),
            is_admin=bool(form.is_admin.data),
            first_login=True,
        )
        db.session.add(user)
        db.session.flush()
        # Audit: user added
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity

            uid = get_jwt_identity()
        except Exception:
            uid = None
        db.session.add(
            AuditLog(
                user_id=int(uid) if uid else None,
                action='user_added',
                target_type='user',
                target_id=user.id,
                details=f"username={user.username}; email={user.email}; is_admin={user.is_admin}",
            )
        )
        db.session.commit()
        flash('User added', 'success')
        return redirect(url_for('users.list_users'))
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return render_template('add_user.html', form=form)


@admin_bp.route('/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id: int):
    form = DeleteForm()
    if form.validate_on_submit():
        user = db.session.get(User, user_id)
        if not user:
            abort(404)
        if user.is_admin:
            flash('Cannot delete admin user', 'danger')
        else:
            # Audit before deletion
            try:
                verify_jwt_in_request()
                from flask_jwt_extended import get_jwt_identity

                uid = get_jwt_identity()
            except Exception:
                uid = None
            db.session.add(
                AuditLog(
                    user_id=int(uid) if uid else None,
                    action='user_deleted',
                    target_type='user',
                    target_id=user.id,
                    details=f"username={user.username}; email={user.email}",
                )
            )
            db.session.delete(user)
            db.session.commit()
            flash('User deleted', 'info')
    return redirect(url_for('users.list_users'))


@admin_bp.route('/make-admin/<int:user_id>', methods=['POST'])
def make_admin(user_id: int):
    """Promote a user to admin."""
    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for('users.list_users'))
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.is_admin:
        flash('User is already an admin', 'info')
        return redirect(url_for('users.list_users'))
    user.is_admin = True
    # Audit: user promoted
    try:
        verify_jwt_in_request()
        from flask_jwt_extended import get_jwt_identity

        uid = get_jwt_identity()
    except Exception:
        uid = None
    db.session.add(
        AuditLog(
            user_id=int(uid) if uid else None,
            action='user_promoted',
            target_type='user',
            target_id=user.id,
            details=f"username={user.username}; email={user.email}",
        )
    )
    db.session.commit()
    flash('User promoted to admin', 'success')
    return redirect(url_for('users.list_users'))


@admin_bp.route('/revoke-admin/<int:user_id>', methods=['POST'])
def revoke_admin(user_id: int):
    """Revoke admin rights from a user with safeguards.

    - Cannot revoke from non-existing or non-admin users.
    - Cannot revoke from 'system' user.
    - Cannot revoke if this would leave no human admins (excluding 'system').
    """
    form = DeleteForm()
    if not form.validate_on_submit():
        return redirect(url_for('users.list_users'))
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if not user.is_admin:
        flash('User is not an admin', 'info')
        return redirect(url_for('users.list_users'))
    if user.username == 'system':
        flash('Cannot revoke admin from system user', 'danger')
        return redirect(url_for('users.list_users'))
    # Prevent revoking from primary admin user defined in config
    try:
        primary_admin = current_app.config.get('USERNAME')
        if primary_admin and user.username == primary_admin:
            flash('Cannot revoke admin from primary admin user', 'danger')
            return redirect(url_for('users.list_users'))
    except Exception:
        pass

    # Prevent self-demotion (current user cannot revoke their own admin)
    try:
        verify_jwt_in_request()
        from flask_jwt_extended import get_jwt_identity

        acting_uid = get_jwt_identity()
    except Exception:
        acting_uid = None
    if acting_uid and int(acting_uid) == int(user.id):
        flash('You cannot revoke your own admin privileges', 'danger')
        return redirect(url_for('users.list_users'))

    # Count current human admins (exclude 'system')
    human_admins = User.query.filter(User.is_admin.is_(True), User.username != 'system').count()
    if human_admins <= 1:
        flash('Cannot revoke admin: at least one admin is required', 'danger')
        return redirect(url_for('users.list_users'))

    user.is_admin = False
    # Audit: user demoted
    # Acting user id for audit (may be None)
    uid = acting_uid if acting_uid is not None else None
    db.session.add(
        AuditLog(
            user_id=int(uid) if uid else None,
            action='user_demoted',
            target_type='user',
            target_id=user.id,
            details=f"username={user.username}; email={user.email}",
        )
    )
    db.session.commit()
    flash('Admin rights revoked', 'success')
    return redirect(url_for('users.list_users'))


@admin_bp.route('/email-settings', methods=['GET', 'POST'])
def email_settings():
    settings = EmailSettings.query.first()
    if not settings:
        settings = EmailSettings(
            from_email='test@example.com',
            to_email='admin@example.com',
            smtp_server='localhost',
            smtp_port=1025,
            smtp_user='',
            smtp_pass='',
        )
        db.session.add(settings)
        db.session.commit()

    form = EmailSettingsForm()
    if form.validate_on_submit():
        # Snapshot current values to compute changes for audit
        old = {
            'from_email': settings.from_email,
            'to_email': settings.to_email,
            'smtp_server': settings.smtp_server,
            'smtp_port': settings.smtp_port,
            'smtp_user': settings.smtp_user or '',
            'smtp_pass': bool(settings.smtp_pass),
        }
        data = EmailSettingsData(
            from_email=form.from_email.data,
            to_email=form.to_email.data,
            smtp_server=form.smtp_server.data,
            smtp_port=int(form.smtp_port.data),
            smtp_user=form.smtp_user.data or '',
            smtp_pass=form.smtp_pass.data or '',
        )
        settings.from_email = data.from_email
        settings.to_email = data.to_email
        settings.smtp_server = data.smtp_server
        settings.smtp_port = data.smtp_port
        settings.smtp_user = data.smtp_user
        settings.smtp_pass = data.smtp_pass
        # Build concise change set (mask password)
        changes = []
        for key in ('from_email', 'to_email', 'smtp_server', 'smtp_port', 'smtp_user'):
            new_val = getattr(settings, key)
            if str(old.get(key)) != str(new_val):
                changes.append(f"{key}:{old.get(key)}->{new_val}")
        # Handle password separately (only note if changed)
        if bool(data.smtp_pass) != bool(old['smtp_pass']):
            changes.append("smtp_pass:updated")
        # Audit: email settings updated
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity

            uid = get_jwt_identity()
        except Exception:
            uid = None
        db.session.add(
            AuditLog(
                user_id=int(uid) if uid else None,
                action='email_settings_updated',
                target_type='email',
                target_id=settings.id,
                details='; '.join(changes)[:255],
            )
        )
        db.session.commit()
        flash('Settings saved', 'success')
        return redirect(url_for('users.email_settings'))
    elif request.method == 'GET':
        form.from_email.data = settings.from_email
        form.to_email.data = settings.to_email
        form.smtp_server.data = settings.smtp_server
        form.smtp_port.data = str(settings.smtp_port)
        form.smtp_user.data = settings.smtp_user
        form.smtp_pass.data = settings.smtp_pass
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return render_template('email_settings.html', form=form)


@admin_bp.route('/schedule', methods=['GET', 'POST'])
def schedule_settings():
    settings = ScheduleSettings.query.first()
    if not settings:
        settings = ScheduleSettings(hour=0, minute=0)
        db.session.add(settings)
        db.session.commit()
    audit_cfg = AuditSettings.query.first()
    if not audit_cfg:
        audit_cfg = AuditSettings(retention_days=90)
        db.session.add(audit_cfg)
        db.session.commit()
    bkp_cfg = BackupSettings.query.first()
    if not bkp_cfg:
        # default to instance/backups
        from flask import current_app as _ca
        default_dir = os.path.join(_ca.instance_path, 'backups') if hasattr(_ca, 'instance_path') else os.path.join(os.getcwd(), 'instance', 'backups')
        bkp_cfg = BackupSettings(directory=default_dir, keep=3)
        db.session.add(bkp_cfg)
        db.session.commit()

    # Prepare forms (GET only here)
    cleanup_form = CleanupScheduleForm()
    backup_form = BackupScheduleForm()
    audit_form = AuditScheduleForm()
    run_form = DeleteForm()
    backup_run_form = DeleteForm()
    cleanup_form.hour.data = settings.hour
    cleanup_form.minute.data = settings.minute
    backup_form.backup_hour.data = settings.backup_hour
    backup_form.backup_minute.data = settings.backup_minute
    backup_form.backup_keep.data = bkp_cfg.keep
    audit_form.audit_retention_days.data = audit_cfg.retention_days
    audit_form.audit_hour.data = settings.audit_hour
    audit_form.audit_minute.data = settings.audit_minute
    # latest backup info (best-effort, ignore errors)
    try:
        latest_path, latest_time = get_latest_backup(current_app._get_current_object(), directory=bkp_cfg.directory)
    except Exception:
        latest_path, latest_time = None, None
    latest_time_str = latest_time.strftime('%Y-%m-%d %H:%M:%S UTC') if latest_time else None
    # Next scheduled run times
    next_cleanup_str = next_backup_str = next_audit_str = None
    try:
        sched = current_app.scheduler
        cj = sched.get_job('cleanup_job') if sched else None
        bj = sched.get_job('backup_job') if sched else None
        if cj and cj.next_run_time:
            next_cleanup_str = cj.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        if bj and bj.next_run_time:
            next_backup_str = bj.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        aj = sched.get_job('audit_purge_job') if sched else None
        if aj and aj.next_run_time:
            next_audit_str = aj.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        pass
    # Fallback compute if scheduler has no jobs
    if not next_cleanup_str:
        now = datetime.utcnow()
        nc = now.replace(hour=settings.hour, minute=settings.minute, second=0, microsecond=0)
        if nc <= now:
            nc = nc + timedelta(days=1)
        next_cleanup_str = nc.strftime('%Y-%m-%d %H:%M:%S UTC')
    if not next_backup_str:
        now = datetime.utcnow()
        nb = now.replace(hour=settings.backup_hour, minute=settings.backup_minute, second=0, microsecond=0)
        if nb <= now:
            nb = nb + timedelta(days=1)
        next_backup_str = nb.strftime('%Y-%m-%d %H:%M:%S UTC')
    if not next_audit_str:
        now = datetime.utcnow()
        na = now.replace(hour=settings.audit_hour, minute=settings.audit_minute, second=0, microsecond=0)
        if na <= now:
            na = na + timedelta(days=1)
        next_audit_str = na.strftime('%Y-%m-%d %H:%M:%S UTC')
    return render_template(
        'schedule_settings.html',
        form=None,
        cleanup_form=cleanup_form,
        backup_form=backup_form,
        audit_form=audit_form,
        run_form=run_form,
        backup_run_form=backup_run_form,
        latest_backup_path=latest_path,
        latest_backup_time=latest_time_str,
        backup_dir=bkp_cfg.directory,
        next_cleanup_time=next_cleanup_str,
        next_backup_time=next_backup_str,
        next_audit_time=next_audit_str,
    )


@admin_bp.route('/schedule/run', methods=['POST'])
def run_cleanup_now():
    run_form = DeleteForm()
    if run_form.validate_on_submit():
        # Run the cleanup job once
        from ..tasks import delete_expired_items
        from flask import current_app

        app = current_app._get_current_object()
        with app.app_context():
            # attribute deletions to the initiating user
            try:
                verify_jwt_in_request()
                from flask_jwt_extended import get_jwt_identity

                uid_del = get_jwt_identity()
            except Exception:
                uid_del = None
            delete_expired_items(initiator_user_id=int(uid_del) if uid_del else None)
            # Audit: manual job run
            try:
                verify_jwt_in_request()
                from flask_jwt_extended import get_jwt_identity

                uid = get_jwt_identity()
            except Exception:
                uid = None
            db.session.add(
                AuditLog(
                    user_id=int(uid) if uid else None,
                    action='cleanup_job_run',
                    target_type='job',
                    target_id=None,
                    details='trigger=manual',
                )
            )
            db.session.commit()
        flash('Cleanup job executed', 'info')
    return redirect(url_for('users.schedule_settings'))


@admin_bp.route('/schedule/cleanup', methods=['POST'])
def save_cleanup_schedule():
    form = CleanupScheduleForm()
    if form.validate_on_submit():
        settings = ScheduleSettings.query.first()
        old_hour, old_minute = settings.hour, settings.minute
        nh, nm = int(form.hour.data), int(form.minute.data)
        # prevent conflict with backup schedule
        if settings.backup_hour == nh and settings.backup_minute == nm:
            flash('Cleanup time must differ from backup time.', 'danger')
            return redirect(url_for('users.schedule_settings'))
        settings.hour = nh
        settings.minute = nm
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity
            uid = get_jwt_identity()
        except Exception:
            uid = None
        if (old_hour != settings.hour) or (old_minute != settings.minute):
            db.session.add(AuditLog(
                user_id=int(uid) if uid else None,
                action='schedule_updated',
                target_type='schedule',
                target_id=settings.id,
                details=f"time:{old_hour:02d}:{old_minute:02d}->{settings.hour:02d}:{settings.minute:02d}",
            ))
        db.session.commit()
        update_cleanup_schedule(current_app._get_current_object())
        flash('Cleanup schedule saved', 'success')
    else:
        for errs in form.errors.values():
            for e in errs:
                flash(e, 'danger')
    return redirect(url_for('users.schedule_settings'))


@admin_bp.route('/schedule/backup', methods=['POST'])
def save_backup_schedule():
    form = BackupScheduleForm()
    if form.validate_on_submit():
        settings = ScheduleSettings.query.first()
        bkp_cfg = BackupSettings.query.first()
        old_bh, old_bm = settings.backup_hour, settings.backup_minute
        old_keep = bkp_cfg.keep if bkp_cfg else None
        nbh, nbm = int(form.backup_hour.data), int(form.backup_minute.data)
        nkeep = int(form.backup_keep.data)
        # prevent conflict with cleanup schedule
        if settings.hour == nbh and settings.minute == nbm:
            flash('Backup time must differ from cleanup time.', 'danger')
            return redirect(url_for('users.schedule_settings'))
        settings.backup_hour = nbh
        settings.backup_minute = nbm
        if not bkp_cfg:
            default_dir = os.path.join(current_app.instance_path, 'backups') if hasattr(current_app, 'instance_path') else os.path.join(os.getcwd(), 'instance', 'backups')
            bkp_cfg = BackupSettings(directory=default_dir, keep=nkeep)
            db.session.add(bkp_cfg)
        else:
            bkp_cfg.keep = nkeep
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity
            uid = get_jwt_identity()
        except Exception:
            uid = None
        if (old_bh != settings.backup_hour) or (old_bm != settings.backup_minute):
            db.session.add(AuditLog(
                user_id=int(uid) if uid else None,
                action='backup_schedule_updated',
                target_type='schedule',
                target_id=settings.id,
                details=f"time:{old_bh:02d}:{old_bm:02d}->{settings.backup_hour:02d}:{settings.backup_minute:02d}",
            ))
        if old_keep is not None and old_keep != bkp_cfg.keep:
            db.session.add(AuditLog(
                user_id=int(uid) if uid else None,
                action='backup_settings_updated',
                target_type='backup',
                target_id=bkp_cfg.id,
                details=f"keep:{old_keep}->{bkp_cfg.keep}",
            ))
        db.session.commit()
        update_backup_schedule(current_app._get_current_object())
        flash('Backup schedule saved', 'success')
    else:
        for errs in form.errors.values():
            for e in errs:
                flash(e, 'danger')
    return redirect(url_for('users.schedule_settings'))


@admin_bp.route('/schedule/audit', methods=['POST'])
def save_audit_schedule():
    form = AuditScheduleForm()
    if form.validate_on_submit():
        settings = ScheduleSettings.query.first()
        audit_cfg = AuditSettings.query.first()
        old_ah, old_am = settings.audit_hour, settings.audit_minute
        old_ret = audit_cfg.retention_days if audit_cfg else None
        nah, nam = int(form.audit_hour.data), int(form.audit_minute.data)
        nret = int(form.audit_retention_days.data)
        settings.audit_hour = nah
        settings.audit_minute = nam
        if not audit_cfg:
            audit_cfg = AuditSettings(retention_days=nret)
            db.session.add(audit_cfg)
        else:
            audit_cfg.retention_days = nret
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity
            uid = get_jwt_identity()
        except Exception:
            uid = None
        if (old_ah != settings.audit_hour) or (old_am != settings.audit_minute):
            db.session.add(AuditLog(
                user_id=int(uid) if uid else None,
                action='audit_schedule_updated',
                target_type='schedule',
                target_id=settings.id,
                details=f"time:{old_ah:02d}:{old_am:02d}->{settings.audit_hour:02d}:{settings.audit_minute:02d}",
            ))
        if old_ret is not None and old_ret != audit_cfg.retention_days:
            db.session.add(AuditLog(
                user_id=int(uid) if uid else None,
                action='audit_retention_updated',
                target_type='audit',
                target_id=audit_cfg.id,
                details=f"retention_days:{old_ret}->{audit_cfg.retention_days}",
            ))
        db.session.commit()
        from ..tasks import update_audit_purge_schedule as _uaps
        _uaps(current_app._get_current_object())
        flash('Audit purge schedule saved', 'success')
    else:
        for errs in form.errors.values():
            for e in errs:
                flash(e, 'danger')
    return redirect(url_for('users.schedule_settings'))


@admin_bp.route('/schedule/backup/run', methods=['POST'])
def run_backup_now():
    backup_run_form = DeleteForm()
    if backup_run_form.validate_on_submit():
        # Run the backup job once
        from flask import current_app

        app = current_app._get_current_object()
        with app.app_context():
            try:
                cfg = BackupSettings.query.first()
                bdir = cfg.directory if cfg else None
                bkeep = cfg.keep if cfg else None
                path = write_backup_file(app, directory=bdir)
                # attribute backup creation to the initiating user
                try:
                    verify_jwt_in_request()
                    from flask_jwt_extended import get_jwt_identity
                    uid = get_jwt_identity()
                except Exception:
                    uid = None
                db.session.add(
                    AuditLog(
                        user_id=int(uid) if uid else None,
                        action='backup_created',
                        target_type='backup',
                        target_id=None,
                        details=f"path={path}; trigger=manual",
                    )
                )
                db.session.commit()
                prune_backups(app, directory=bdir, keep=bkeep)
                flash('Backup created', 'info')
            except Exception as e:
                db.session.rollback()
                flash(f'Backup failed: {e}', 'danger')
    return redirect(url_for('users.schedule_settings'))


# -------------------- Backup & Restore --------------------


class BackupUser(BaseModel):
    id: int
    username: str
    email: str
    hashed_password: str
    is_admin: bool = False
    first_login: bool = True


class BackupList(BaseModel):
    id: int
    name: str
    type: str


class BackupItem(BaseModel):
    id: int
    category: str
    data: str
    description: Optional[str] = None
    date: datetime | str
    creator_id: Optional[int] = None


class BackupEmailSettings(BaseModel):
    id: int
    from_email: str
    to_email: str
    smtp_server: str
    smtp_port: int
    smtp_user: Optional[str] = ''
    smtp_pass: Optional[str] = ''


class BackupScheduleSettings(BaseModel):
    id: int
    hour: int
    minute: int
    backup_hour: Optional[int] = None
    backup_minute: Optional[int] = None
    audit_hour: Optional[int] = None
    audit_minute: Optional[int] = None


class BackupAudit(BaseModel):
    id: int
    created_at: datetime
    user_id: Optional[int] = None
    actor_name: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[int] = None
    list_id: Optional[int] = None
    details: Optional[str] = None


class BackupAuditSettings(BaseModel):
    id: int
    retention_days: int


class BackupBackupSettings(BaseModel):
    # Export/import only the retention count; directory is local-only
    keep: int


class BackupPayload(BaseModel):
    version: int = 1
    created_at: datetime
    users: List[BackupUser] = Field(default_factory=list)
    lists: List[BackupList] = Field(default_factory=list)
    items: List[BackupItem] = Field(default_factory=list)
    email_settings: Optional[BackupEmailSettings] = None
    schedule_settings: Optional[BackupScheduleSettings] = None
    audits: List[BackupAudit] = Field(default_factory=list)
    # optional: audit settings
    audit_settings: Optional[BackupAuditSettings] = None
    # optional: backup settings
    backup_settings: Optional[BackupBackupSettings] = None


@admin_bp.route('/backup', methods=['GET'])
def backup_page():
    download_form = BackupDownloadForm()
    restore_form = BackupRestoreForm()
    return render_template('backup.html', download_form=download_form, restore_form=restore_form)


@admin_bp.route('/backup/download', methods=['POST'])
def backup_download():
    form = BackupDownloadForm()
    if not form.validate_on_submit():
        flash('Invalid request', 'danger')
        return redirect(url_for('users.backup_page'))

    payload_dict = build_backup_payload(current_app._get_current_object())
    payload = BackupPayload.model_validate(payload_dict)
    data = payload.model_dump(mode='json')
    fname = f"wgui-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    # Audit: backup downloaded
    try:
        verify_jwt_in_request()
        from flask_jwt_extended import get_jwt_identity
        uid = get_jwt_identity()
    except Exception:
        uid = None
    try:
        db.session.add(
            AuditLog(
                user_id=int(uid) if uid else None,
                action='backup_downloaded',
                target_type='backup',
                target_id=None,
                details=f"filename={fname}",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
    resp = Response(
        json.dumps(data, ensure_ascii=False, separators=(',', ':')),
        mimetype='application/json'
    )
    resp.headers['Content-Disposition'] = f'attachment; filename={fname}'
    return resp


@admin_bp.route('/backup/restore', methods=['POST'])
def backup_restore():
    form = BackupRestoreForm()
    if not form.validate_on_submit() or not form.file.data:
        flash('Invalid upload', 'danger')
        return redirect(url_for('users.backup_page'))

    try:
        raw = form.file.data.read()
        obj = json.loads(raw)
        payload = BackupPayload.model_validate(obj)
    except (json.JSONDecodeError, ValidationError) as e:
        flash(f'Invalid backup file: {e}', 'danger')
        return redirect(url_for('users.backup_page'))

    # Restore transactionally
    try:
        # Clear dependent tables first (items, audits), then lists/users/settings
        db.session.query(DataList).delete()
        db.session.query(AuditLog).delete()
        db.session.query(ListModel).delete()
        db.session.query(User).delete()
        db.session.query(EmailSettings).delete()
        db.session.query(ScheduleSettings).delete()
        db.session.query(AuditSettings).delete()
        db.session.query(BackupSettings).delete()
        db.session.flush()

        # Users
        for u in payload.users:
            db.session.add(
                User(
                    id=u.id,
                    username=u.username,
                    email=u.email,
                    hashed_password=u.hashed_password,
                    is_admin=bool(u.is_admin),
                    first_login=bool(u.first_login),
                )
            )
        db.session.flush()

        # Lists
        for l in payload.lists:
            db.session.add(ListModel(id=l.id, name=l.name, type=l.type))
        db.session.flush()

        # Items
        from datetime import date as _date
        for it in payload.items:
            # Allow string or datetime for date
            dval = it.date
            if isinstance(dval, str):
                # Parse ISO formats; fallback to simple YYYY-MM-DD
                try:
                    d = datetime.fromisoformat(dval).date()
                except Exception:
                    d = _date.fromisoformat(dval)
            else:
                d = dval.date() if hasattr(dval, 'date') else dval
            db.session.add(
                DataList(
                    id=it.id,
                    category=it.category,
                    data=it.data,
                    description=it.description,
                    date=d,
                    creator_id=it.creator_id,
                )
            )
        db.session.flush()

        # Email settings (single row)
        if payload.email_settings:
            es = payload.email_settings
            db.session.add(
                EmailSettings(
                    id=es.id,
                    from_email=es.from_email,
                    to_email=es.to_email,
                    smtp_server=es.smtp_server,
                    smtp_port=es.smtp_port,
                    smtp_user=es.smtp_user or '',
                    smtp_pass=es.smtp_pass or '',
                )
            )

        # Schedule settings (single row)
        if payload.schedule_settings:
            ss = payload.schedule_settings
            db.session.add(ScheduleSettings(
                id=ss.id,
                hour=ss.hour,
                minute=ss.minute,
                backup_hour=(ss.backup_hour if ss.backup_hour is not None else 0),
                backup_minute=(ss.backup_minute if ss.backup_minute is not None else 0),
                audit_hour=(ss.audit_hour if ss.audit_hour is not None else 0),
                audit_minute=(ss.audit_minute if ss.audit_minute is not None else 0),
            ))

        # Audit settings (single row)
        if payload.audit_settings:
            aus = payload.audit_settings
            db.session.add(AuditSettings(id=aus.id, retention_days=aus.retention_days))

        # Backup settings (single row) - keep path managed locally, restore only 'keep'
        if payload.backup_settings:
            bks = payload.backup_settings
            # default folder under instance/backups
            default_dir = os.path.join(current_app.instance_path, 'backups') if hasattr(current_app, 'instance_path') else os.path.join(os.getcwd(), 'instance', 'backups')
            db.session.add(BackupSettings(directory=default_dir, keep=bks.keep))

        # Audits
        for a in payload.audits:
            db.session.add(
                AuditLog(
                    id=a.id,
                    created_at=a.created_at,
                    user_id=a.user_id,
                    actor_name=a.actor_name,
                    action=a.action,
                    target_type=a.target_type,
                    target_id=a.target_id,
                    list_id=a.list_id,
                    details=a.details,
                )
            )

        db.session.commit()
        # reschedule background tasks according to restored settings
        app_obj = current_app._get_current_object()
        update_cleanup_schedule(app_obj)
        update_backup_schedule(app_obj)
        try:
            from ..tasks import update_audit_purge_schedule as _uaps
            _uaps(app_obj)
        except Exception:
            pass
        # audit restore summary
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity
            uid = get_jwt_identity()
        except Exception:
            uid = None
        try:
            db.session.add(
                AuditLog(
                    user_id=int(uid) if uid else None,
                    action='backup_restored',
                    target_type='backup',
                    target_id=None,
                    details=f"users={len(payload.users)}; lists={len(payload.lists)}; items={len(payload.items)}; audits={len(payload.audits)}",
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        flash('Backup restored successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to restore backup: {e}', 'danger')

    return redirect(url_for('users.backup_page'))
