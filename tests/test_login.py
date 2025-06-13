import pytest


def test_login_success(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
    assert b'Welcome!' in resp.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') == 1


def test_login_failure(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid credentials' in resp.data





def test_add_user_password_mismatch(client, login):
    login()
    resp = client.post('/users/add', data={
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'secret',
        'confirm_password': 'wrong'
    }, follow_redirects=True)
    assert b'Passwords must match' in resp.data


def test_admin_user_management(client, login):
    login()
    # add user
    resp = client.post('/users/add', data={
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'secret',
        'confirm_password': 'secret'
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


def test_session_timeout_one_hour(client):
    resp = client.post(
        '/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True
    )
    cookie = resp.headers.get('Set-Cookie')
    from http.cookies import SimpleCookie
    from datetime import datetime, timedelta

    simple = SimpleCookie()
    simple.load(cookie)
    exp = simple['session']['expires']
    assert exp  # expires attribute is set
    from datetime import timezone
    expire_dt = datetime.strptime(exp, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc)
    delta = expire_dt - datetime.now(timezone.utc)
    assert timedelta(minutes=59) <= delta <= timedelta(hours=1, minutes=1)


def test_account_requires_login(client):
    resp = client.get('/account', follow_redirects=True)
    assert b'Login' in resp.data


def test_update_account(client, login):
    login()
    from wgui.models import User
    from wgui.extensions import db
    with client.application.app_context():
        orig_user = db.session.get(User, 1)
        old_hash = orig_user.hashed_password
    resp = client.post(
        '/account',
        data={
            'email': 'new@example.com',
            'password': 'newpass',
            'confirm_password': 'newpass',
        },
        follow_redirects=True,
    )
    assert b'Account updated' in resp.data
    with client.application.app_context():
        user = db.session.get(User, 1)
        assert user.email == 'new@example.com'
        assert user.hashed_password != old_hash
    # logout and login with new password
    client.get('/logout')
    resp = login(password='newpass')
    assert b'Welcome!' in resp.data
