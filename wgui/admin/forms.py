from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField
from flask_wtf.file import FileField, FileAllowed, FileRequired
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
    backup_hour = IntegerField('Backup Hour (0-23)', validators=[InputRequired(), NumberRange(min=0, max=23)])
    backup_minute = IntegerField('Backup Minute (0-59)', validators=[InputRequired(), NumberRange(min=0, max=59)])
    audit_hour = IntegerField('Audit Purge Hour (0-23)', validators=[InputRequired(), NumberRange(min=0, max=23)])
    audit_minute = IntegerField('Audit Purge Minute (0-59)', validators=[InputRequired(), NumberRange(min=0, max=59)])
    audit_retention_days = IntegerField('Audit Retention (days)', validators=[InputRequired(), NumberRange(min=1, max=3650)])
    backup_keep = IntegerField('Keep Last N Backups', validators=[InputRequired(), NumberRange(min=1, max=50)])


class CleanupScheduleForm(FlaskForm):
    hour = IntegerField('Hour (0-23)', validators=[InputRequired(), NumberRange(min=0, max=23)])
    minute = IntegerField('Minute (0-59)', validators=[InputRequired(), NumberRange(min=0, max=59)])


class BackupScheduleForm(FlaskForm):
    backup_hour = IntegerField('Backup Hour (0-23)', validators=[InputRequired(), NumberRange(min=0, max=23)])
    backup_minute = IntegerField('Backup Minute (0-59)', validators=[InputRequired(), NumberRange(min=0, max=59)])
    backup_keep = IntegerField('Keep Last N Backups', validators=[InputRequired(), NumberRange(min=1, max=50)])


class AuditScheduleForm(FlaskForm):
    audit_hour = IntegerField('Audit Purge Hour (0-23)', validators=[InputRequired(), NumberRange(min=0, max=23)])
    audit_minute = IntegerField('Audit Purge Minute (0-59)', validators=[InputRequired(), NumberRange(min=0, max=59)])
    audit_retention_days = IntegerField('Audit Retention (days)', validators=[InputRequired(), NumberRange(min=1, max=3650)])


class BackupDownloadForm(FlaskForm):
    """Empty form for CSRF protection when triggering a backup download."""
    pass


class BackupRestoreForm(FlaskForm):
    """Upload a backup JSON file to restore."""
    file = FileField('Backup JSON', validators=[
        FileRequired(),
        FileAllowed(['json'], 'JSON files only!'),
    ])
