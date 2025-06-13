from flask import Blueprint, render_template, redirect, url_for, flash, session
from ..models import DataList, ListModel
from ..extensions import db
from .forms import AddItemForm, DeleteForm, AddListForm
from .models import AddItemData, AddListData

lists_bp = Blueprint('lists', __name__, url_prefix='/lists')


@lists_bp.app_context_processor
def inject_lists():
    lists_by_type = {'Ip': [], 'Ip Range': [], 'String': []}
    for lst in ListModel.query.all():
        lists_by_type.setdefault(lst.type, []).append(lst)
    return {'lists_by_type': lists_by_type}


@lists_bp.before_request
def require_login():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))


@lists_bp.route('/add', methods=['GET', 'POST'])
def add_list():
    form = AddListForm()
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
    lst = ListModel.query.get_or_404(list_id)
    items = DataList.query.filter_by(category=lst.name).all()
    delete_form = DeleteForm()
    return render_template('list_items.html', list=lst, items=items, delete_form=delete_form)


@lists_bp.route('/<int:list_id>/add', methods=['GET', 'POST'])
def add_item(list_id: int):
    lst = ListModel.query.get_or_404(list_id)
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
        item = DataList.query.get_or_404(item_id)
        category = item.category
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted', 'info')
        lst = ListModel.query.filter_by(name=category).first()
        if lst:
            return redirect(url_for('lists.list_items', list_id=lst.id))
        return redirect(url_for('auth.index'))
    return redirect(url_for('auth.index'))
