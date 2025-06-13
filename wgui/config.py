import os
from werkzeug.security import generate_password_hash


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
    USERNAME = os.environ.get('APP_USERNAME', 'admin')
    # default password is 'admin'
    PASSWORD_HASH = os.environ.get(
        'APP_PASSWORD_HASH',
        generate_password_hash('admin'),
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///wgui.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
