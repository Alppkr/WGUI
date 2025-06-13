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
