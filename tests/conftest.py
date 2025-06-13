import sys
from pathlib import Path

# add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from wgui import create_app
from wgui.extensions import db
from werkzeug.security import generate_password_hash
from wgui.models import User


@pytest.fixture
def client():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:'
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(User(
            username='admin',
            email='admin@example.com',
            hashed_password=generate_password_hash('admin'),
            is_admin=True,
        ))
        db.session.commit()
    with app.test_client() as client:
        yield client


@pytest.fixture
def login(client):
    def _login(username='admin', password='admin'):
        return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)
    return _login
