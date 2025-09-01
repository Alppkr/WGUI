from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
)
from flask_jwt_extended import (
    create_access_token,
    set_access_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
    get_jwt_identity,
    get_jwt,
)
from werkzeug.security import check_password_hash, generate_password_hash
from ..models import User, DataList, ListModel
from ..extensions import db
from .forms import LoginForm, ChangeEmailForm, ChangePasswordForm
from .models import LoginData, ChangeEmailData, ChangePasswordData


auth_bp = Blueprint('auth', __name__)


@auth_bp.app_context_processor
def inject_current_user():
    user = None
    claims = {}
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        claims = get_jwt()
        if user_id:
            user = db.session.get(User, int(user_id))
    except Exception:
        pass
    return {
        'current_user': user,
        'current_claims': claims,
        'password_form': ChangePasswordForm(),
        'email_form': ChangeEmailForm(),
    }


@auth_bp.route('/', methods=['GET'])
def index():
    try:
        verify_jwt_in_request()
    except Exception:
        return redirect(url_for('auth.login'))
    # Optional global search across all lists
    q = request.args.get('q', '').strip()

    # Build upcoming deletion summaries
    from datetime import date, timedelta

    today = date.today()
    td3 = timedelta(days=3)
    td7 = timedelta(days=7)
    td30 = timedelta(days=30)

    upcoming_top10 = (
        DataList.query.filter(DataList.date >= today)
        .order_by(DataList.date.asc())
        .limit(10)
        .all()
    )
    in_3_days = (
        DataList.query.filter(DataList.date >= today, DataList.date <= today + td3)
        .order_by(DataList.date.asc())
        .all()
    )
    # Overlapping ranges: 1 week includes items in 3 days; 1 month includes all up to 30 days
    in_1_week = (
        DataList.query.filter(DataList.date >= today, DataList.date <= today + td7)
        .order_by(DataList.date.asc())
        .all()
    )
    in_1_month = (
        DataList.query.filter(DataList.date >= today, DataList.date <= today + td30)
        .order_by(DataList.date.asc())
        .all()
    )

    # Map list name to type/id for nice labels and links
    lists = ListModel.query.all()
    types_by_name = {l.name: l.type for l in lists}
    ids_by_name = {l.name: l.id for l in lists}

    # Global search results (substring match)
    search_results = []
    if q:
        search_results = DataList.query.filter(DataList.data.contains(q)).all()

    return render_template(
        'home.html',
        q=q,
        search_results=search_results,
        upcoming_top10=upcoming_top10,
        in_3_days=in_3_days,
        in_1_week=in_1_week,
        in_1_month=in_1_month,
        types_by_name=types_by_name,
        ids_by_name=ids_by_name,
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = LoginData(username=form.username.data, password=form.password.data)
        user = User.query.filter_by(username=data.username).first()
        if user and check_password_hash(user.hashed_password, data.password):
            session.permanent = True
            access_token = create_access_token(
                identity=str(user.id), additional_claims={'is_admin': user.is_admin}
            )
            resp = redirect(url_for('auth.index'))
            set_access_cookies(resp, access_token)
            flash('Logged in successfully.', 'success')
            return resp
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    resp = redirect(url_for('auth.login'))
    unset_jwt_cookies(resp)
    flash('Logged out', 'info')
    return resp



def _get_logged_in_user():
    try:
        verify_jwt_in_request()
    except Exception:
        return None
    user_id = get_jwt_identity()
    if not user_id:
        return None
    user = db.session.get(User, int(user_id))
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
