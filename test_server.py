import logging
import mock
import pytest

@pytest.yield_fixture
def twilio_client():
    with mock.patch('twilio.rest.TwilioRestClient') as twilio_client:
        yield twilio_client.return_value

@pytest.fixture
def app(twilio_client):
    logging.basicConfig(level=logging.DEBUG)
    from server import app as my_app
    return my_app

def test_ring(client, twilio_client):
    assert client.get('/ring').status_code == 200
    assert twilio_client.messages.create.call_count == 1

def test_longpoll(client, twilio_client):
    assert client.get('/longpoll_open?timeout=1').data == 'punt'
    r = client.post('/incoming_text', data=dict(From='', Body='y'))
    assert r.status_code == 200
    assert "Opening door" in r.data
    assert client.get('/longpoll_open?timeout=1').data == 'open'
    assert twilio_client.messages.create.call_count == 0
