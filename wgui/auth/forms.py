from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, ValidationError


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class UpdateAccountForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm Password', validators=[Optional()])

    def validate_confirm_password(self, field):
        if self.password.data:
            if not field.data:
                raise ValidationError('Please confirm your new password')
            if field.data != self.password.data:
                raise ValidationError('Passwords must match')
