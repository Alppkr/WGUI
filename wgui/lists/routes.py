from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask import request
from ..models import DataList
from ..extensions import db
from .forms import AddItemForm, DeleteForm
from .models import AddItemData

lists_bp = Blueprint('lists', __name__, url_prefix='/lists')


@lists_bp.before_request
def require_login():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))


@lists_bp.route('/<category>/')
def list_items(category: str):
    items = DataList.query.filter_by(category=category).all()
    delete_form = DeleteForm()
    return render_template('list_items.html', category=category, items=items, delete_form=delete_form)


@lists_bp.route('/<category>/add', methods=['GET', 'POST'])
def add_item(category: str):
    form = AddItemForm()
    if form.validate_on_submit():
        data = AddItemData(
            data=form.data.data,
            description=form.description.data,
            date=form.date.data,
        )
        item = DataList(
            category=category,
            data=data.data,
            description=data.description,
            date=data.date,
        )
        db.session.add(item)
        db.session.commit()
        flash('Item added', 'success')
        return redirect(url_for('lists.list_items', category=category))
    return render_template('add_item.html', form=form, category=category)


@lists_bp.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id: int):
    form = DeleteForm()
    if form.validate_on_submit():
        item = DataList.query.get_or_404(item_id)
        category = item.category
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted', 'info')
        return redirect(url_for('lists.list_items', category=category))
    return redirect(url_for('auth.index'))
