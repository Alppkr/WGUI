from datetime import date



def test_add_and_delete_item(client, login):
    login()
    client.post('/lists/add', data={'name': 'My IPs', 'list_type': 'Ip'}, follow_redirects=True)
    from wgui.models import ListModel
    with client.application.app_context():
        lst = ListModel.query.filter_by(name='My IPs').first()
        list_id = lst.id
    resp = client.post(f'/lists/{list_id}/add', data={
        'data': '1.1.1.1',
        'description': 'cloudflare',
        'date': '2025-06-13'
    }, follow_redirects=True)
    assert b'Item added' in resp.data
    assert b'1.1.1.1' in resp.data

    # fetch item id from app context
    from wgui.models import DataList
    with client.application.app_context():
        item = DataList.query.filter_by(data='1.1.1.1').first()
        assert item is not None
        item_id = item.id

    resp = client.post(f'/lists/delete/{item_id}', follow_redirects=True)
    assert b'Item deleted' in resp.data
    assert b'1.1.1.1' not in resp.data


def test_lists_require_login(client):
    from wgui.models import ListModel
    from wgui.extensions import db
    with client.application.app_context():
        lst = ListModel(name='Temp', type='Ip')
        db.session.add(lst)
        db.session.commit()
        list_id = lst.id
    resp = client.get(f'/lists/{list_id}/', follow_redirects=True)
    assert b'Login' in resp.data


def test_add_list(client, login):
    login()
    resp = client.post(
        '/lists/add',
        data={'name': 'My List', 'list_type': 'Ip'},
        follow_redirects=True,
    )
    assert b'List created' in resp.data
    assert b'My List' in resp.data


def test_lists_grouped_by_type(client, login):
    login()
    client.post('/lists/add', data={'name': 'IP Test', 'list_type': 'Ip'}, follow_redirects=True)
    client.post('/lists/add', data={'name': 'Range Test', 'list_type': 'Ip Range'}, follow_redirects=True)
    resp = client.get('/', follow_redirects=True)
    ip_pos = resp.data.index(b'Ip')
    ip_list_pos = resp.data.index(b'IP Test')
    ip_range_pos = resp.data.index(b'Ip Range')
    range_list_pos = resp.data.index(b'Range Test')
    assert ip_pos < ip_list_pos
    assert ip_range_pos < range_list_pos


def test_plus_button_sets_type(client, login):
    """Plus button includes type parameter so form knows which type."""
    login()
    resp = client.get('/', follow_redirects=True)
    assert b'/lists/add?type=Ip' in resp.data
    assert b'/lists/add?type=Ip+Range' in resp.data
    assert b'/lists/add?type=String' in resp.data


def test_export_list(client):
    from wgui.models import ListModel, DataList
    from wgui.extensions import db
    with client.application.app_context():
        lst = ListModel(name='Export', type='Ip')
        db.session.add(lst)
        db.session.flush()
        db.session.add(
            DataList(category=lst.name, data='1.2.3.4', description='', date=date(2025, 6, 13))
        )
        db.session.commit()
    resp = client.get('/lists/ip/export.txt')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('text/plain')
    assert resp.data.startswith(b'type=ip\n')
    assert b'1.2.3.4' in resp.data


def test_copy_button_present(client, login):
    login()
    client.post('/lists/add', data={'name': 'CopyList', 'list_type': 'Ip'}, follow_redirects=True)
    from wgui.models import ListModel
    with client.application.app_context():
        lst = ListModel.query.filter_by(name='CopyList').first()
        list_id = lst.id
    resp = client.get(f'/lists/{list_id}/', follow_redirects=True)
    assert b'id="copyLink"' in resp.data


def test_delete_expired_items_task(client, login):
    """Expired list items should be removed by the Celery task."""
    from datetime import date, timedelta
    login()
    from wgui.models import ListModel, DataList
    from wgui.extensions import db
    with client.application.app_context():
        lst = ListModel(name='Cleanup', type='Ip')
        db.session.add(lst)
        db.session.flush()
        expired = DataList(
            category=lst.name,
            data='1.1.1.1',
            description='',
            date=date.today() - timedelta(days=1),
        )
        db.session.add(expired)
        db.session.commit()
        assert DataList.query.count() == 1
    from wgui.tasks import delete_expired_items
    with client.application.app_context():
        delete_expired_items()
    with client.application.app_context():
        assert DataList.query.count() == 0


def test_expiration_notifications(client, login, monkeypatch):
    """Items nearing expiration should trigger email notifications."""
    from datetime import date, timedelta
    login()
    sent = []

    def fake_send(subject, body):
        sent.append((subject, body))

    monkeypatch.setattr('wgui.tasks.send_email', fake_send)
    from wgui.models import ListModel, DataList
    from wgui.extensions import db
    with client.application.app_context():
        lst = ListModel(name='Notify', type='Ip')
        db.session.add(lst)
        db.session.flush()
        item = DataList(
            category=lst.name,
            data='9.9.9.9',
            description='',
            date=date.today() + timedelta(days=3),
        )
        db.session.add(item)
        db.session.commit()
    from wgui.tasks import delete_expired_items
    with client.application.app_context():
        delete_expired_items()
    assert sent and 'expiring soon' in sent[0][0].lower()


def test_removal_notification(client, login, monkeypatch):
    """Deleting expired items should send an email with removed entries."""
    from datetime import date, timedelta
    login()
    sent = []

    def fake_send(subject, body):
        sent.append((subject, body))

    monkeypatch.setattr('wgui.tasks.send_email', fake_send)
    from wgui.models import ListModel, DataList
    from wgui.extensions import db
    with client.application.app_context():
        lst = ListModel(name='Expire', type='Ip')
        db.session.add(lst)
        db.session.flush()
        item = DataList(
            category=lst.name,
            data='8.8.8.8',
            description='',
            date=date.today() - timedelta(days=1),
        )
        db.session.add(item)
        db.session.commit()
    from wgui.tasks import delete_expired_items
    with client.application.app_context():
        delete_expired_items()
    assert any('removed' in s[0].lower() for s in sent)
