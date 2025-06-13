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
from ..models import DataList, ListModel
from ..extensions import db
from flask_jwt_extended import verify_jwt_in_request
from .forms import AddItemForm, DeleteForm, AddListForm
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
            db.session.commit()
            flash('List created', 'success')
            return redirect(url_for('lists.list_items', list_id=new_list.id))
    return render_template('add_list.html', form=form)


@lists_bp.route('/<int:list_id>/')
def list_items(list_id: int):
    lst = db.session.get(ListModel, list_id)
    if not lst:
        abort(404)
    items = DataList.query.filter_by(category=lst.name).all()
    delete_form = DeleteForm()
    return render_template('list_items.html', list=lst, items=items, delete_form=delete_form)


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
        item = DataList(
            category=lst.name,
            data=data.data,
            description=data.description,
            date=data.date,
        )
        db.session.add(item)
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
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted', 'info')
        lst = ListModel.query.filter_by(name=category).first()
        if lst:
            return redirect(url_for('lists.list_items', list_id=lst.id))
        return redirect(url_for('auth.index'))
    return redirect(url_for('auth.index'))


@lists_bp.route('/<list_type>/<list_name>.txt')
def export_list(list_type: str, list_name: str):
    """Export a list as plain text using type and name in the URL."""
    def matches(lst: ListModel) -> bool:
        return slugify(lst.type) == list_type and slugify(lst.name) == list_name

    lst = next((l for l in ListModel.query.all() if matches(l)), None)
    if not lst:
        abort(404)
    items = DataList.query.filter_by(category=lst.name).all()
    content = "\n".join(item.data for item in items)
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={lst.name}.txt"},
    )
