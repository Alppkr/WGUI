import pytest


def test_404_handler(client):
    resp = client.get('/nonexistent')
    assert resp.status_code == 404
    assert b'The requested page was not found.' in resp.data


def test_pydantic_validation_error(client):
    resp = client.get('/raise-validation-error')
    assert resp.status_code == 400
    assert b'Bad Request' in resp.data
