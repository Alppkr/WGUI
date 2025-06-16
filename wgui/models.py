from .extensions import db


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
