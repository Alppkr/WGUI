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

from ..models import User, EmailSettings
from ..extensions import db
from .forms import AddUserForm, DeleteForm, EmailSettingsForm
from .models import AddUserData, EmailSettingsData

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
