from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
)
from werkzeug.security import check_password_hash, generate_password_hash
from ..models import User
from ..extensions import db
from .forms import LoginForm, ChangeEmailForm, ChangePasswordForm
from .models import LoginData, ChangeEmailData, ChangePasswordData


auth_bp = Blueprint('auth', __name__)


@auth_bp.app_context_processor
def inject_current_user():
    user = None
    if session.get('user_id'):
        user = db.session.get(User, session['user_id'])
    return {
        'current_user': user,
        'password_form': ChangePasswordForm(),
        'email_form': ChangeEmailForm(),
    }


@auth_bp.route('/', methods=['GET'])
def index():
    if session.get('logged_in'):
        return render_template('home.html')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = LoginData(username=form.username.data, password=form.password.data)
        user = User.query.filter_by(username=data.username).first()
        if user and check_password_hash(user.hashed_password, data.password):
            session.permanent = True
            session['logged_in'] = True
            session['is_admin'] = user.is_admin
            session['user_id'] = user.id
            flash('Logged in successfully.', 'success')
            return redirect(url_for('auth.index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('is_admin', None)
    session.pop('user_id', None)
    flash('Logged out', 'info')
    return redirect(url_for('auth.login'))



def _get_logged_in_user():
    if not session.get('logged_in'):
        return None
    user_id = session.get('user_id')
    if not user_id:
        session.clear()
        return None
    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return None
    return user


@auth_bp.route('/account/email', methods=['POST'])
def update_email():
    user = _get_logged_in_user()
    if not user:
        return redirect(url_for('auth.login'))
    form = ChangeEmailForm()
    if form.validate_on_submit():
        data = ChangeEmailData(email=form.email.data)
        user.email = data.email
        db.session.commit()
        flash('Email updated', 'success')
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return redirect(request.referrer or url_for('auth.index'))


@auth_bp.route('/account/password', methods=['POST'])
def update_password():
    user = _get_logged_in_user()
    if not user:
        return redirect(url_for('auth.login'))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        data = ChangePasswordData(password=form.password.data)
        user.hashed_password = generate_password_hash(data.password)
        db.session.commit()
        flash('Password updated', 'success')
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return redirect(request.referrer or url_for('auth.index'))
