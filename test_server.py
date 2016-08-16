import logging
import mock
import pytest

@pytest.yield_fixture
def twilio_client():
    with mock.patch('twilio.rest.TwilioRestClient'):
        with mock.patch('doorbell.server.twilio_client') as twilio_client:
            yield twilio_client

@pytest.yield_fixture
def target_phones():
    phones = ['+15555555555', '+13333333333']
    with mock.patch('doorbell.server.TARGET_PHONES', phones):
        yield phones

@pytest.fixture
def app(twilio_client):
    logging.basicConfig(level=logging.DEBUG)
    from doorbell.server import app as my_app
    return my_app

def test_ring(client, twilio_client, target_phones):
    assert client.get('/ring').status_code == 200
    assert twilio_client.messages.create.call_count == len(target_phones)

def test_longpoll(client, twilio_client, target_phones):
    assert client.get('/longpoll_open?timeout=1').data == 'punt'
    r = client.post('/incoming_text', data=dict(From=target_phones[1], Body='y'))
    assert r.status_code == 200
    assert "Opening door" in r.data
    assert client.get('/longpoll_open?timeout=1').data == 'open'
    assert twilio_client.messages.create.call_count == len(target_phones)
