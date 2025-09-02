from flask import Blueprint, render_template, request, redirect, url_for
from ..i18n import _
from flask_jwt_extended import verify_jwt_in_request
from ..models import AuditLog, User, ListModel
from sqlalchemy import or_, and_, cast, String
from datetime import datetime, timedelta


logs_bp = Blueprint('logs', __name__, url_prefix='/logs')

# Canonical action keys used in DB
ACTIONS = [
    'list_added', 'list_deleted', 'list_edited',
    'item_added', 'item_deleted', 'item_edited',
    # admin/user and settings actions
    'user_added', 'user_deleted',
    'email_settings_updated', 'schedule_updated', 'backup_schedule_updated', 'audit_schedule_updated', 'audit_retention_updated',
    # scheduled job actions
    'cleanup_job_run', 'backup_created', 'backup_settings_updated', 'audit_purge_run',
    # auth and backup ops
    'login_success', 'login_failed', 'logout',
    'user_email_changed', 'user_password_changed',
    'backup_downloaded', 'backup_restored',
    # export
    'list_exported',
    # user role changes
    'user_promoted',
    'user_demoted',
]


@logs_bp.app_template_filter('humanize_action')
def humanize_action(value: str) -> str:
    mapping = {
        'list_added': 'new list added',
        'list_deleted': 'list deleted',
        'list_edited': 'list edited',
        'item_added': 'item added',
        'item_deleted': 'item deleted',
        'item_edited': 'item edited',
        'user_added': 'user added',
        'user_deleted': 'user deleted',
        'email_settings_updated': 'email settings updated',
        'schedule_updated': 'schedule updated',
        'backup_schedule_updated': 'backup schedule updated',
        'audit_schedule_updated': 'audit purge schedule updated',
        'audit_retention_updated': 'audit retention updated',
        'cleanup_job_run': 'cleanup job run',
        'backup_created': 'backup created',
        'backup_settings_updated': 'backup settings updated',
        'audit_purge_run': 'audit logs purged',
        'login_success': 'login success',
        'login_failed': 'login failed',
        'logout': 'logout',
        'user_email_changed': 'user email changed',
        'user_password_changed': 'user password changed',
        'backup_downloaded': 'backup downloaded',
        'backup_restored': 'backup restored',
        'list_exported': 'list exported',
        'user_promoted': 'user promoted to admin',
        'user_demoted': 'user demoted from admin',
    }
    if not value:
        return ''
    # Return a localized, human-friendly string
    return _(mapping.get(value, value.replace('_', ' ')))


@logs_bp.app_template_filter('entry_value')
def entry_value(row) -> str:
    """Extract the entry/list name for add/delete actions.

    - item_added/item_deleted: returns the item's data value.
    - list_added/list_deleted: returns the list name.
    For other actions, returns empty string.
    """
    try:
        action = getattr(row, 'action', '') or ''
        details = getattr(row, 'details', '') or ''

        def extract(details_str: str, key: str) -> str:
            if not details_str:
                return ''
            token = key + '='
            if token not in details_str:
                return ''
            frag = details_str.split(token, 1)[1]
            return frag.split(';', 1)[0].strip()

        if action in ('item_added', 'item_deleted'):
            return extract(details, 'data')
        if action in ('list_added', 'list_deleted'):
            # prefer joined list if present
            if getattr(row, 'list', None) and getattr(row.list, 'name', None):
                return row.list.name
            return extract(details, 'name')
        if action in ('user_added', 'user_deleted', 'user_promoted', 'user_demoted'):
            return extract(details, 'username')
        return ''
    except Exception:
        return ''

# Backward-compat alias in case templates still use removed_entry
removed_entry = entry_value


@logs_bp.app_template_filter('target_display')
def target_display(row) -> str:
    """Human-readable target label. For user targets, show the username.
    Falls back to list label or default type/id.
    """
    try:
        # For user targets, show real username from details snapshot
        if getattr(row, 'target_type', '') == 'user':
            details = getattr(row, 'details', '') or ''
            token = 'username='
            if token in details:
                frag = details.split(token, 1)[1]
                name = frag.split(';', 1)[0].strip()
                if name:
                    return f"user {name}"
        # For list targets, prefer joined list type.name
        if getattr(row, 'list', None) and getattr(row.list, 'name', None):
            return f"{row.list.type.lower().replace(' ', '')}.{row.list.name.lower().replace(' ', '')}"
        # Default
        t = (getattr(row, 'target_type', '') or '').strip()
        i = getattr(row, 'target_id', None)
        return f"{t} {i}".strip()
    except Exception:
        return ''


@logs_bp.before_request
def require_login():
    try:
        verify_jwt_in_request()
    except Exception:
        return redirect(url_for('auth.login'))


@logs_bp.route('/')
def audit():
    """Audit page with filters (action, list, user, date range) and pagination."""
    action_raw = request.args.get('action', type=str)
    # Normalize action input: support human text like "list deleted"
    def _canon(v: str | None) -> str | None:
        if not v:
            return None
        x = v.strip().lower().replace('-', ' ').replace('_', ' ')
        x = '_'.join([p for p in x.split() if p])
        if x in ACTIONS:
            return x
        # partial match to known actions
        for a in ACTIONS:
            if x in a:
                return a
        return x

    action = _canon(action_raw)
    list_id = request.args.get('list_id', type=int)  # deprecated, kept for backward-compat
    # Support both legacy 'list_name' and new 'target_name' param
    list_name = request.args.get('list_name', type=str)
    target_name = request.args.get('target_name', type=str)
    if (not list_name) and target_name:
        list_name = target_name
    user_id = request.args.get('user_id', type=int)  # deprecated, kept for backward-compat
    username = request.args.get('username', type=str)
    entry = request.args.get('entry', type=str)
    start = request.args.get('start', type=str)
    end = request.args.get('end', type=str)
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=50, type=int)
    if per_page < 1:
        per_page = 50
    if per_page > 200:
        per_page = 200

    q = AuditLog.query.order_by(AuditLog.created_at.desc())
    if action:
        if action in ACTIONS:
            q = q.filter(AuditLog.action == action)
        else:
            q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if list_id:
        q = q.filter(AuditLog.list_id == list_id)
    if list_name:
        # Search by what the Target column shows:
        # - For list-related rows: match ListModel.type and/or ListModel.name.
        #   UI shows "type.name" (lower, spaces removed) but we approximate with ilike.
        # - For non-list rows: match target_type or target_id.
        tn = (list_name or '').strip()
        q = q.join(ListModel, isouter=True)
        list_cond = or_(
            ListModel.type.ilike(f"%{tn}%"),
            ListModel.name.ilike(f"%{tn}%"),
        )
        if '.' in tn:
            left, right = tn.split('.', 1)
            list_cond = and_(
                ListModel.type.ilike(f"%{left.strip()}%"),
                ListModel.name.ilike(f"%{right.strip()}%"),
            )
        non_list_cond = or_(
            AuditLog.target_type.ilike(f"%{tn}%"),
            cast(AuditLog.target_id, String).ilike(f"%{tn}%"),
        )
        q = q.filter(or_(list_cond, non_list_cond))
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if username:
        # case-insensitive match on username
        q = q.join(User, isouter=True).filter(User.username.ilike(f"%{username}%"))
    if entry:
        # match entry value in details (works for item data or list name)
        like = f"%{entry}%"
        q = q.filter(
            or_(
                AuditLog.details.ilike(f"%data={entry}%"),
                AuditLog.details.ilike(f"%name={entry}%"),
                AuditLog.details.ilike(like),
            )
        )

    # Date range parsing (YYYY-MM-DD)
    start_dt = None
    end_dt = None
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            start_dt = None
    if end:
        try:
            # include entire end day
            end_dt = datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            q = q.filter(AuditLog.created_at <= end_dt)
        except ValueError:
            end_dt = None

    total = q.count()
    logs = q.offset((page - 1) * per_page).limit(per_page).all()
    has_prev = page > 1
    has_next = page * per_page < total
    start_index = (page - 1) * per_page + (1 if total else 0)
    end_index = min(page * per_page, total)

    return render_template(
        'audit.html',
        logs=logs,
        total=total,
        page=page,
        per_page=per_page,
        has_prev=has_prev,
        has_next=has_next,
        start_index=start_index,
        end_index=end_index,
        # echo filters back to template
        action=action,
        list_name=list_name,
        username=username,
        entry=entry,
        start=start,
        end=end,
        actions=ACTIONS,
    )
