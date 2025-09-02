import os
from datetime import timedelta
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
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_COOKIE_CSRF_PROTECT = False
    # Audit logging throttle for login failures
    LOGIN_FAIL_LOG_WINDOW_SECONDS = int(os.environ.get('LOGIN_FAIL_LOG_WINDOW_SECONDS', '60'))
    LOGIN_FAIL_LOG_MAX_PER_WINDOW = int(os.environ.get('LOGIN_FAIL_LOG_MAX_PER_WINDOW', '5'))
    # Backups
    BACKUP_DIR = os.environ.get('BACKUP_DIR') or os.path.join(
        os.environ.get('INSTANCE_PATH', os.path.join(os.getcwd(), 'instance')),
        'backups',
    )
    BACKUP_KEEP = int(os.environ.get('BACKUP_KEEP', '3'))
