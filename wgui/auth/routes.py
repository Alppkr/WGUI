from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
    abort,
)
from werkzeug.security import check_password_hash, generate_password_hash
from ..models import User
from ..extensions import db
from .forms import LoginForm, UpdateAccountForm
from .models import LoginData, UpdateAccountData


auth_bp = Blueprint('auth', __name__)


@auth_bp.app_context_processor
def inject_current_user():
    user = None
    if session.get('user_id'):
        user = db.session.get(User, session['user_id'])
    return {'current_user': user}


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


@auth_bp.route('/account', methods=['GET', 'POST'])
def account():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    form = UpdateAccountForm()
    user = db.session.get(User, session.get('user_id'))
    if not user:
        abort(404)
    if request.method == 'GET':
        form.email.data = user.email
    if form.validate_on_submit():
        data = UpdateAccountData(
            email=form.email.data or None,
            password=form.password.data or None,
        )
        if data.email:
            user.email = data.email
        if data.password:
            user.hashed_password = generate_password_hash(data.password)
        db.session.commit()
        flash('Account updated', 'success')
        return redirect(url_for('auth.account'))
    elif request.method == 'POST':
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return render_template('account.html', form=form)
