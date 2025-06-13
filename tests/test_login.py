import pytest
from wgui import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client


def test_login_success(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
    assert b'Welcome!' in resp.data


def test_login_failure(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid credentials' in resp.data
