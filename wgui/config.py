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
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'memory://')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'cache+memory://')
