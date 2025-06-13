from datetime import date



def test_add_and_delete_item(client, login):
    login()
    resp = client.post('/lists/ip/add', data={
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
    resp = client.get('/lists/ip/', follow_redirects=True)
    assert b'Login' in resp.data
