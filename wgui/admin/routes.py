from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from werkzeug.security import generate_password_hash

from ..models import User
from ..extensions import db
from .forms import AddUserForm, DeleteForm
from .models import AddUserData

admin_bp = Blueprint('users', __name__, url_prefix='/users')


def admin_required():
    return session.get('logged_in') and session.get('is_admin')


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
        user = User.query.get_or_404(user_id)
        if user.is_admin:
            flash('Cannot delete admin user', 'danger')
        else:
            db.session.delete(user)
            db.session.commit()
            flash('User deleted', 'info')
    return redirect(url_for('users.list_users'))
