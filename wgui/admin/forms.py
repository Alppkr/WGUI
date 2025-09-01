from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField
from wtforms.validators import DataRequired, InputRequired, Email, EqualTo, NumberRange


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
    to_email = StringField('To', validators=[DataRequired()])
    smtp_server = StringField('SMTP Server', validators=[DataRequired()])
    smtp_port = StringField('SMTP Port', validators=[DataRequired()])
    smtp_user = StringField('SMTP User')
    smtp_pass = PasswordField('SMTP Pass')


class ScheduleSettingsForm(FlaskForm):
    # Use InputRequired so 0 is accepted; DataRequired treats 0 as missing.
    hour = IntegerField('Hour (0-23)', validators=[InputRequired(), NumberRange(min=0, max=23)])
    minute = IntegerField('Minute (0-59)', validators=[InputRequired(), NumberRange(min=0, max=59)])
