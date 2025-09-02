from flask_wtf import FlaskForm
from wtforms import StringField, DateField, HiddenField
from wtforms.validators import DataRequired

class AddItemForm(FlaskForm):
    data = StringField('Data', validators=[DataRequired()])
    description = StringField('Description')
    date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')

class DeleteForm(FlaskForm):
    """Simple form for CSRF protection when deleting list items."""
    pass


class AddListForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    list_type = HiddenField(validators=[DataRequired()])


class EditListForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])


class EditItemForm(FlaskForm):
    data = StringField('Data', validators=[DataRequired()])
    description = StringField('Description')
    date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
