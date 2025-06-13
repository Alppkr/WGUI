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
        db.drop_all()
        db.create_all()
        from wgui.models import User
        from werkzeug.security import generate_password_hash
        db.session.add(User(
            username='admin',
            email='admin@example.com',
            hashed_password=generate_password_hash('admin'),
            is_admin=True,
        ))
        db.session.commit()
    with app.test_client() as client:
        yield client


def test_login_success(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
    assert b'Welcome!' in resp.data


def test_login_failure(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid credentials' in resp.data


def login(client, username='admin', password='admin'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_admin_user_management(client):
    login(client)
    # add user
    resp = client.post('/users/add', data={
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'secret'
    }, follow_redirects=True)
    assert b'User added' in resp.data
    assert b'bob@example.com' in resp.data
    # fetch user id
    from wgui.models import User
    with client.application.app_context():
        user = User.query.filter_by(username='bob').first()
        assert user is not None
        user_id = user.id
    # delete user
    resp = client.post(f'/users/delete/{user_id}', follow_redirects=True)
    assert b'User deleted' in resp.data
    assert b'bob@example.com' not in resp.data


def test_users_requires_login(client):
    resp = client.get('/users/', follow_redirects=True)
    assert b'Login' in resp.data
