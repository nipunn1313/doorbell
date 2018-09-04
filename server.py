import enum
import logging
import os
import threading
import time

import twilio.twiml

from flask import (
    Flask,
    request,
)
from raven.contrib.flask import Sentry
from twilio.rest import TwilioRestClient

twilio_client = TwilioRestClient(
    account=os.getenv('TWILIO_API_SID'),
    token=os.getenv('TWILIO_API_TOKEN'),
    request_account=os.getenv('TWILIO_ACCOUNT_SID'),
)

TARGET_PHONES = os.getenv('TARGET_PHONES', '').split(',')
TWILIO_PHONE = os.getenv('TWILIO_PHONE')

app = Flask(__name__)
sentry = Sentry(app, level=logging.INFO)

class DoorState(enum.Enum):
    NEUTRAL = 1
    RECENTLY_BUZZED = 2
    OPEN = 3
    PARTY_MODE_NEUTRAL = 4
    PARTY_MODE_OPEN = 5

class DoorManager(object):
    def __init__(self):
        # type: () -> None
        self.state_cond = threading.Condition()

        self.state = DoorState.NEUTRAL
        self.last_state_change_ts = 0.0

    def _set_state(self, state):
        # type: (DoorState) -> None
        self.state = state
        self.last_state_change_ts = time.time()
        logging.info("State changed to %s", self.state)
        self.state_cond.notify()

    def party_mode(self, who):
        # type: (str) -> None
        """Enable party mode!"""
        send_texts('Party mode enabled by %s' % who)
        with self.state_cond:
            self._set_state(DoorState.PARTY_MODE_OPEN)

    def regular_mode(self, who):
        # type: (str) -> None
        send_texts('Party mode disabled by %s' % who)
        with self.state_cond:
            self._set_state(DoorState.NEUTRAL)

    def buzz(self):
        # type: () -> None
        """Called by raspberry pi when someone buzzes"""
        with self.state_cond:
            if self.state in (DoorState.PARTY_MODE_NEUTRAL, DoorState.PARTY_MODE_OPEN):
                send_texts('Someone rang the doorbell. '
                           'Opening w/ party mode. Respond with "r" for regular mode.')
                self._set_state(DoorState.PARTY_MODE_OPEN)
            else:
                send_texts('Someone rang the doorbell. '
                           'Respond with "y" to open door. Respond with "p" for party mode.')
                self._set_state(DoorState.RECENTLY_BUZZED)

    def open(self, who):
        # type: (str) -> None
        """Called by twilio to open door"""
        with self.state_cond:
            if self.state == DoorState.RECENTLY_BUZZED:
                if time.time() <= self.last_state_change_ts + 60.0:
                    send_texts('Door opened by %s' % who)
                    self._set_state(DoorState.OPEN)
                else:
                    self._set_state(DoorState.NEUTRAL)
            else:
                send_texts('Door open request from %s refused. Buzzer not recently buzzed' % who)

    def _should_open(self):
        # type: () -> bool
        logging.info("At %s, last_state_change_ts=%s", time.time(), self.last_state_change_ts)
        return (
            self.state in (DoorState.OPEN, DoorState.PARTY_MODE_OPEN) and
            self.last_state_change_ts <= time.time() <= self.last_state_change_ts + 10.0
        )

    def longpoll_open(self, timeout):
        # type: (float) -> str
        """Called by the raspberry pi to figure out when to open the door"""
        poll_end = time.time() + timeout
        with self.state_cond:
            while not self._should_open() and time.time() <= poll_end:
                self.state_cond.wait(timeout=poll_end - time.time())

            if self._should_open():
                if self.state == DoorState.PARTY_MODE_OPEN:
                    self._set_state(DoorState.PARTY_MODE_NEUTRAL)
                else:
                    self._set_state(DoorState.NEUTRAL)

                return 'open'

            return 'punt'

door_manager = DoorManager()
def reset():
    # type: () -> None
    global door_manager
    door_manager = DoorManager()

def send_texts(text_message):
    # type: (str) -> None
    logging.info("Sending: %s", text_message)
    for to in TARGET_PHONES:
        message = twilio_client.messages.create(
            body=text_message,
            to=to,
            from_=TWILIO_PHONE,
        )
        logging.info("Message(%s) sent to %s. Status: %s", message.sid, to, message.status)

@app.route("/incoming_text", methods=['GET', 'POST'])
def incoming_text():
    # type: () -> str
    """Handle incoming texts"""
    who = request.values.get('From')
    body = request.values.get('Body', '')

    logging.debug('Received message from %s:\n%s', who, body)
    resp = twilio.twiml.Response()

    if who not in TARGET_PHONES:
        logging.info("Text was from a rogue number %s. Ignoring.", who)
    elif body in ('y', 'Y', 'yes', 'Yes'):
        door_manager.open(who)
    elif body in ('p', 'P', 'party', 'Party'):
        door_manager.party_mode(who)
    return str(resp)

@app.route("/ring", methods=['GET'])
def ring():
    # type: () -> str
    door_manager.buzz()
    return 'ok'

@app.route("/longpoll_open", methods=['GET'])
def longpoll_open():
    # type: () -> str
    timeout = float(request.args.get('timeout', 60.0))
    return door_manager.longpoll_open(timeout=timeout)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    port = int(os.getenv('PORT', 8080))
    ip = os.getenv('IP', '0.0.0.0')
    logging.info("Starting doorbell server on %s:%s", ip, port)
    app.run(debug=False, host=ip, port=port, threaded=True)
