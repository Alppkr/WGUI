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
from ..models import DataList, ListModel, AuditLog
from ..extensions import db
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from .forms import AddItemForm, DeleteForm, AddListForm, EditListForm, EditItemForm
from .models import AddItemData, AddListData


lists_bp = Blueprint('lists', __name__, url_prefix='/lists')


def slugify(text: str) -> str:
    """Simple slugify function used for export URLs."""
    return text.lower().replace(" ", "-")


@lists_bp.app_template_filter("slugify")
def slugify_filter(s: str) -> str:
    return slugify(s)


@lists_bp.app_context_processor
def inject_lists():
    lists_by_type = {'Ip': [], 'Ip Range': [], 'String': []}
    for lst in ListModel.query.all():
        lists_by_type.setdefault(lst.type, []).append(lst)
    return {'lists_by_type': lists_by_type}


@lists_bp.before_request
def require_login():
    """Require authentication for all list routes except exports."""
    if request.endpoint == 'lists.export_list':
        return
    try:
        verify_jwt_in_request()
    except Exception:
        return redirect(url_for('auth.login'))


@lists_bp.route('/add', methods=['GET', 'POST'])
def add_list():
    form = AddListForm()
    if request.method == 'GET':
        default_type = request.args.get('type')
        if default_type:
            form.list_type.data = default_type
    if form.validate_on_submit():
        data = AddListData(name=form.name.data, type=form.list_type.data)
        if ListModel.query.filter_by(name=data.name).first():
            flash('List already exists', 'danger')
        else:
            new_list = ListModel(name=data.name, type=data.type)
            db.session.add(new_list)
            db.session.flush()
            try:
                verify_jwt_in_request()
                from flask_jwt_extended import get_jwt_identity

                uid = get_jwt_identity()
            except Exception:
                uid = None
            db.session.add(
                AuditLog(
                    user_id=int(uid) if uid else None,
                    action='list_added',
                    target_type='list',
                    target_id=new_list.id,
                    list_id=new_list.id,
                    details=f"name={new_list.name}; type={new_list.type}",
                )
            )
            db.session.commit()
            flash('List created', 'success')
            return redirect(url_for('lists.list_items', list_id=new_list.id))
    return render_template('add_list.html', form=form)


@lists_bp.route('/<int:list_id>/edit', methods=['GET', 'POST'])
def edit_list(list_id: int):
    lst = db.session.get(ListModel, list_id)
    if not lst:
        abort(404)
    form = EditListForm()
    if form.validate_on_submit():
        new_name = form.name.data.strip()
        if not new_name:
            flash('Name is required', 'danger')
            return redirect(url_for('lists.edit_list', list_id=list_id))
        exists = ListModel.query.filter(ListModel.name == new_name, ListModel.id != list_id).first()
        if exists:
            flash('Another list with this name already exists', 'danger')
            return redirect(url_for('lists.edit_list', list_id=list_id))
        old_name = lst.name
        if new_name != old_name:
            lst.name = new_name
            # Update items category to match new list name
            DataList.query.filter_by(category=old_name).update({DataList.category: new_name})
            db.session.commit()
            flash('List renamed', 'success')
        else:
            flash('No changes made', 'info')
        return redirect(url_for('lists.list_items', list_id=list_id))
    elif request.method == 'GET':
        form.name.data = lst.name
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return render_template('edit_list.html', form=form, list=lst)


@lists_bp.route('/<int:list_id>/')
def list_items(list_id: int):
    lst = db.session.get(ListModel, list_id)
    if not lst:
        abort(404)
    search = request.args.get('q', '').strip()
    items = DataList.query.filter_by(category=lst.name).all()
    if search:
        import re
        try:
            regex = re.compile(search)
            items = [
                i
                for i in items
                if regex.search(i.data) or (i.description and regex.search(i.description))
            ]
        except re.error:
            items = [
                i
                for i in items
                if (search in i.data) or (i.description and search in i.description)
            ]
    delete_form = DeleteForm()
    return render_template(
        'list_items.html',
        list=lst,
        items=items,
        delete_form=delete_form,
        search=search,
    )


@lists_bp.route('/<int:list_id>/add', methods=['GET', 'POST'])
def add_item(list_id: int):
    lst = db.session.get(ListModel, list_id)
    if not lst:
        abort(404)
    form = AddItemForm()
    if form.validate_on_submit():
        data = AddItemData(
            data=form.data.data,
            description=form.description.data,
            date=form.date.data,
        )
        exists = DataList.query.filter_by(category=lst.name, data=data.data).first()
        if exists:
            flash('Item already exists', 'danger')
        else:
            # Determine the current user from JWT
            user_id = None
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
            except Exception:
                user_id = None
            item = DataList(
                category=lst.name,
                data=data.data,
                description=data.description,
                date=data.date,
                creator_id=int(user_id) if user_id else None,
            )
            db.session.add(item)
            db.session.flush()
            db.session.add(
                AuditLog(
                    user_id=int(user_id) if user_id else None,
                    action='item_added',
                    target_type='item',
                    target_id=item.id,
                    list_id=lst.id,
                    details=f"category={lst.name}; data={item.data}",
                )
            )
            db.session.commit()
            flash('Item added', 'success')
            return redirect(url_for('lists.list_items', list_id=list_id))
    return render_template('add_item.html', form=form, list=lst)


@lists_bp.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id: int):
    form = DeleteForm()
    if form.validate_on_submit():
        item = db.session.get(DataList, item_id)
        if not item:
            abort(404)
        category = item.category
        # Audit before deletion to keep target_id
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity

            uid = get_jwt_identity()
        except Exception:
            uid = None
        db.session.add(
            AuditLog(
                user_id=int(uid) if uid else None,
                action='item_deleted',
                target_type='item',
                target_id=item.id,
                list_id=ListModel.query.filter_by(name=category).first().id if ListModel.query.filter_by(name=category).first() else None,
                details=f"category={category}; data={item.data}",
            )
        )
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted', 'info')
        lst = ListModel.query.filter_by(name=category).first()
        if lst:
            return redirect(url_for('lists.list_items', list_id=lst.id))
        return redirect(url_for('auth.index'))
    return redirect(url_for('auth.index'))


@lists_bp.route('/<int:list_id>/delete', methods=['POST'])
def delete_list(list_id: int):
    """Delete an entire list and its items."""
    form = DeleteForm()
    if form.validate_on_submit():
        lst = db.session.get(ListModel, list_id)
        if not lst:
            abort(404)
        # Audit the deletion
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt_identity

            uid = get_jwt_identity()
        except Exception:
            uid = None
        db.session.add(
            AuditLog(
                user_id=int(uid) if uid else None,
                action='list_deleted',
                target_type='list',
                target_id=lst.id,
                list_id=lst.id,
                details=f"name={lst.name}; type={lst.type}",
            )
        )
        # Delete all items in this list
        items = DataList.query.filter_by(category=lst.name).all()
        for item in items:
            db.session.delete(item)
        # Delete the list itself
        db.session.delete(lst)
        db.session.commit()
        flash('List deleted', 'info')
        return redirect(url_for('auth.index'))
    return redirect(url_for('auth.index'))


@lists_bp.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id: int):
    item = db.session.get(DataList, item_id)
    if not item:
        abort(404)
    lst = ListModel.query.filter_by(name=item.category).first()
    form = EditItemForm()
    if form.validate_on_submit():
        new_data = form.data.data.strip()
        new_desc = form.description.data
        new_date = form.date.data
        if not new_data:
            flash('Data is required', 'danger')
            return redirect(url_for('lists.edit_item', item_id=item_id))
        # enforce uniqueness per (category, data)
        exists = (
            DataList.query
            .filter(DataList.category == item.category, DataList.data == new_data, DataList.id != item.id)
            .first()
        )
        if exists:
            flash('An entry with this value already exists in this list', 'danger')
            return redirect(url_for('lists.edit_item', item_id=item_id))
        item.data = new_data
        item.description = new_desc
        item.date = new_date
        db.session.commit()
        flash('Entry updated', 'success')
        if lst:
            return redirect(url_for('lists.list_items', list_id=lst.id))
        return redirect(url_for('auth.index'))
    elif request.method == 'GET':
        form.data.data = item.data
        form.description.data = item.description
        form.date.data = item.date
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, 'danger')
    return render_template('edit_item.html', form=form, list=lst, item=item)


@lists_bp.route('/<list_type>/<list_name>.txt')
def export_list(list_type: str, list_name: str):
    """Export a list as plain text using type and name in the URL."""
    def matches(lst: ListModel) -> bool:
        return slugify(lst.type) == list_type and slugify(lst.name) == list_name

    lst = next((l for l in ListModel.query.all() if matches(l)), None)
    if not lst:
        abort(404)
    items = DataList.query.filter_by(category=lst.name).all()
    header = f"type={slugify(lst.type)}"
    lines = [header] + [item.data for item in items]
    content = "\n".join(lines)
    # Audit export (optional auth)
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
    except Exception:
        uid = None
    try:
        from ..models import AuditLog
        db.session.add(
            AuditLog(
                user_id=int(uid) if uid else None,
                action='list_exported',
                target_type='list',
                target_id=lst.id,
                list_id=lst.id,
                details=f"name={lst.name}; type={lst.type}; ip={request.remote_addr}",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={lst.name}.txt"},
    )
