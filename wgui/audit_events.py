from flask import g
from sqlalchemy import event
from sqlalchemy.orm.attributes import get_history
from .extensions import db
from .models import AuditLog, DataList, ListModel


@event.listens_for(db.session, 'before_flush')
def audit_edits(session, flush_context, instances):
    """Automatically log edits to DataList and ListModel before flush.

    Creates an AuditLog with action 'item_edited' or 'list_edited' when fields change.
    Relies on g.user_id set by a Flask before_request.
    """
    try:
        user_id = int(getattr(g, 'user_id', None)) if getattr(g, 'user_id', None) else None
    except Exception:
        user_id = None

    for obj in session.dirty.copy():
        # Skip if the row is being deleted
        if session.is_modified(obj, include_collections=False):
            if isinstance(obj, DataList):
                changes = []
                for attr in ['data', 'description', 'date', 'category']:
                    hist = get_history(obj, attr)
                    if hist.has_changes():
                        old = hist.deleted[0] if hist.deleted else None
                        new = hist.added[0] if hist.added else None
                        if old != new:
                            changes.append(f"{attr}:{old}->{new}")
                if changes:
                    # Resolve list_id from category if possible
                    list_id = None
                    try:
                        lst = ListModel.query.filter_by(name=obj.category).first()
                        list_id = lst.id if lst else None
                    except Exception:
                        list_id = None
                    session.add(
                        AuditLog(
                            user_id=user_id,
                            action='item_edited',
                            target_type='item',
                            target_id=obj.id,
                            list_id=list_id,
                            details='; '.join(changes)[:255],
                        )
                    )
            elif isinstance(obj, ListModel):
                changes = []
                for attr in ['name', 'type']:
                    hist = get_history(obj, attr)
                    if hist.has_changes():
                        old = hist.deleted[0] if hist.deleted else None
                        new = hist.added[0] if hist.added else None
                        if old != new:
                            changes.append(f"{attr}:{old}->{new}")
                if changes:
                    session.add(
                        AuditLog(
                            user_id=user_id,
                            action='list_edited',
                            target_type='list',
                            target_id=obj.id,
                            list_id=obj.id,
                            details='; '.join(changes)[:255],
                        )
                    )

