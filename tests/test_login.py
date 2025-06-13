import pytest


def test_login_success(client):
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
    assert b'Account' in resp.data
    assert ('localhost', '/', 'access_token_cookie') in client._cookies


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
        '/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=False
    )
    cookie = resp.headers.get('Set-Cookie')
    from http.cookies import SimpleCookie
    from datetime import datetime, timedelta

    simple = SimpleCookie()
    simple.load(cookie)
    token = simple['access_token_cookie'].value
    from flask_jwt_extended import decode_token
    from datetime import timezone
    payload = decode_token(token)
    expire_dt = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
    delta = expire_dt - datetime.now(timezone.utc)
    assert timedelta(minutes=59) <= delta <= timedelta(hours=1, minutes=1)


def test_account_requires_login(client):
    resp = client.post('/account/email', follow_redirects=True)
    assert b'Login' in resp.data


def test_update_email_and_password(client, login):
    login()
    from wgui.models import User
    from wgui.extensions import db
    with client.application.app_context():
        orig_user = db.session.get(User, 1)
        old_hash = orig_user.hashed_password
    resp = client.post('/account/email', data={'email': 'new@example.com'}, follow_redirects=True)
    assert b'Email updated' in resp.data
    resp = client.post(
        '/account/password',
        data={'password': 'newpass', 'confirm_password': 'newpass'},
        follow_redirects=True,
    )
    assert b'Password updated' in resp.data
    with client.application.app_context():
        user = db.session.get(User, 1)
        assert user.email == 'new@example.com'
        assert user.hashed_password != old_hash
    client.get('/logout')
    resp = login(password='newpass')
    assert b'Account' in resp.data


def test_update_password_mismatch(client, login):
    login()
    resp = client.post(
        '/account/password',
        data={'password': 'abc', 'confirm_password': 'xyz'},
        follow_redirects=True,
    )
    assert b'Passwords must match' in resp.data


def test_account_dropdown(client, login):
    resp = login()
    assert b'Change Password' in resp.data
    assert b'Change Email' in resp.data
    assert b'admin@example.com' in resp.data


def test_email_settings_update(client, login):
    login()
    resp = client.get('/users/email-settings', follow_redirects=True)
    assert b'Email Settings' in resp.data
    resp = client.post(
        '/users/email-settings',
        data={
            'from_email': 'a@example.com',
            'to_email': 'b@example.com',
            'smtp_server': 'smtp.example.com',
            'smtp_port': '25',
            'smtp_user': 'u',
            'smtp_pass': 'p',
        },
        follow_redirects=True,
    )
    assert b'Settings saved' in resp.data
    from wgui.models import EmailSettings
    with client.application.app_context():
        settings = EmailSettings.query.first()
        assert settings.smtp_server == 'smtp.example.com'
