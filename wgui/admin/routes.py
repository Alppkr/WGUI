from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
)
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from werkzeug.security import generate_password_hash

from ..models import User, EmailSettings, ScheduleSettings, AuditLog
from ..extensions import db
from .forms import AddUserForm, DeleteForm, EmailSettingsForm, ScheduleSettingsForm
from .models import AddUserData, EmailSettingsData
from ..tasks import update_cleanup_schedule

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
            is_admin=False,
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
                details=f"username={user.username}; email={user.email}",
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

    form = ScheduleSettingsForm()
    run_form = DeleteForm()
    if form.validate_on_submit():
        old_hour = settings.hour
        old_minute = settings.minute
        settings.hour = int(form.hour.data)
        settings.minute = int(form.minute.data)
        # Audit: schedule updated
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity

            uid = get_jwt_identity()
        except Exception:
            uid = None
        change_str = f"time:{old_hour:02d}:{old_minute:02d}->{settings.hour:02d}:{settings.minute:02d}"
        db.session.add(
            AuditLog(
                user_id=int(uid) if uid else None,
                action='schedule_updated',
                target_type='schedule',
                target_id=settings.id,
                details=change_str,
            )
        )
        db.session.commit()
        # reschedule job
        from flask import current_app

        update_cleanup_schedule(current_app._get_current_object())
        flash('Schedule updated', 'success')
        return redirect(url_for('users.schedule_settings'))
    elif request.method == 'GET':
        form.hour.data = settings.hour
        form.minute.data = settings.minute
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return render_template('schedule_settings.html', form=form, run_form=run_form)


@admin_bp.route('/schedule/run', methods=['POST'])
def run_cleanup_now():
    run_form = DeleteForm()
    if run_form.validate_on_submit():
        # Run the cleanup job once
        from ..tasks import delete_expired_items
        from flask import current_app

        app = current_app._get_current_object()
        with app.app_context():
            delete_expired_items()
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
