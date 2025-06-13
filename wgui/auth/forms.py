from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class UpdateAccountForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[Optional(), EqualTo('password', message='Passwords must match')],
    )
