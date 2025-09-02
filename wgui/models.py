from .extensions import db
from sqlalchemy import func


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hashed_password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    first_login = db.Column(db.Boolean, default=True)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class ListModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)

    def __repr__(self) -> str:
        return f"<List {self.name}>"

class DataList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    data = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    date = db.Column(db.Date, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', lazy='joined')
    __table_args__ = (
        db.UniqueConstraint('category', 'data', name='uix_category_data'),
    )

    def __repr__(self) -> str:
        return f"<DataList {self.category} {self.data}>"


class EmailSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_email = db.Column(db.String(120), nullable=False)
    to_email = db.Column(db.String(120), nullable=False)
    smtp_server = db.Column(db.String(120), nullable=False)
    smtp_port = db.Column(db.Integer, nullable=False)
    smtp_user = db.Column(db.String(120))
    smtp_pass = db.Column(db.String(120))

    def __repr__(self) -> str:
        return f"<EmailSettings {self.smtp_server}:{self.smtp_port}>"


class ScheduleSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hour = db.Column(db.Integer, nullable=False, default=0)
    minute = db.Column(db.Integer, nullable=False, default=0)
    # Separate backup schedule
    backup_hour = db.Column(db.Integer, nullable=False, default=0)
    backup_minute = db.Column(db.Integer, nullable=False, default=0)
    # Separate audit purge schedule
    audit_hour = db.Column(db.Integer, nullable=False, default=0)
    audit_minute = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<ScheduleSettings {self.hour:02d}:{self.minute:02d}>"


class AuditSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Number of days to keep audit logs
    retention_days = db.Column(db.Integer, nullable=False, default=90)

    def __repr__(self) -> str:
        return f"<AuditSettings retention_days={self.retention_days}>"


class BackupSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    directory = db.Column(db.String(255), nullable=False)
    keep = db.Column(db.Integer, nullable=False, default=3)

    def __repr__(self) -> str:
        return f"<BackupSettings dir={self.directory} keep={self.keep}>"


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', lazy='joined')
    # Snapshot of actor's username at log time to preserve display after deletion
    actor_name = db.Column(db.String(120))
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)  # 'list' or 'item'
    target_id = db.Column(db.Integer)
    list_id = db.Column(db.Integer, db.ForeignKey('list_model.id'), nullable=True)
    list = db.relationship('ListModel', foreign_keys=[list_id], lazy='joined')
    details = db.Column(db.String(255))

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.target_type}:{self.target_id}>"
