from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo


class AddUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')],
    )


class DeleteForm(FlaskForm):
    """Simple form for CSRF protection when deleting users."""
    pass


class EmailSettingsForm(FlaskForm):
    from_email = StringField('From', validators=[DataRequired(), Email()])
    to_email = StringField('To', validators=[DataRequired(), Email()])
    smtp_server = StringField('SMTP Server', validators=[DataRequired()])
    smtp_port = StringField('SMTP Port', validators=[DataRequired()])
    smtp_user = StringField('SMTP User')
    smtp_pass = PasswordField('SMTP Pass')
