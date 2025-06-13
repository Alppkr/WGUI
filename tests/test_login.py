import pytest
from wgui import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:'
    )
    from wgui.extensions import db
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        yield client


def test_login_success(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
    assert b'Welcome!' in resp.data


def test_login_failure(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid credentials' in resp.data
