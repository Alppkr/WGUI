from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from werkzeug.security import check_password_hash
from ..models import User
from .forms import LoginForm
from .models import LoginData


auth_bp = Blueprint('auth', __name__)


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
            session['logged_in'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('auth.index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out', 'info')
    return redirect(url_for('auth.login'))
