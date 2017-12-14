import logging
import os
import threading
import time

import twilio.twiml

from flask import (
    Flask,
    request,
)
from twilio.rest import TwilioRestClient

twilio_client = TwilioRestClient(
    account=os.getenv('TWILIO_API_SID'),
    token=os.getenv('TWILIO_API_TOKEN'),
    request_account=os.getenv('TWILIO_ACCOUNT_SID'),
)

TARGET_PHONES = os.getenv('TARGET_PHONES', '').split(',')
TWILIO_PHONE = os.getenv('TWILIO_PHONE')

app = Flask(__name__)

class DoorOpener(object):
    def __init__(self):
        self.open_door_ts = 0.0
        self.open_cond = threading.Condition()

    def open(self):
        with self.open_cond:
            self.open_door_ts = time.time()
            logging.info("Set open_door_ts=%s", self.open_door_ts)
            self.open_cond.notify()

    def _should_open(self):
        logging.info("At %s, open_door_ts=%s", time.time(), self.open_door_ts)
        return self.open_door_ts <= time.time() <= self.open_door_ts + 10.0

    def wait_until_open(self, timeout):
        poll_end = time.time() + timeout
        with self.open_cond:
            while not self._should_open() and time.time() <= poll_end:
                self.open_cond.wait(timeout=poll_end - time.time())

            return 'open' if self._should_open() else 'punt'

door_opener = DoorOpener()

def send_texts(text_message):
    for to in TARGET_PHONES:
        message = twilio_client.messages.create(
            body=text_message,
            to=to,
            from_=TWILIO_PHONE,
        )
        logging.info("Message(%s) sent to %s. Status: %s", message.sid, to, message.status)

@app.route("/incoming_text", methods=['GET', 'POST'])
def incoming_text():
    """Handle incoming texts"""
    who = request.values.get('From')
    body = request.values.get('Body', '')

    logging.debug('Received message from %s:\n%s', who, body)
    resp = twilio.twiml.Response()

    if who not in TARGET_PHONES:
        logging.info("Text was from a rogue number %s. Ignoring.", who)
    elif body in ('y', 'Y', 'yes', 'Yes'):
        logging.info('Door opened by %s', who)
        send_texts('Door opened by %s' % who)
        door_opener.open()
    return str(resp)

@app.route("/ring", methods=['GET'])
def ring():
    logging.info("Someone rang the door")
    send_texts('Someone rang the doorbell. Respond with "y" to open door')
    return 'ok'

@app.route("/longpoll_open", methods=['GET'])
def longpoll_open():
    timeout = float(request.args.get('timeout', 60.0))
    return door_opener.wait_until_open(timeout=timeout)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    port = int(os.getenv('PORT'))
    ip = os.getenv('IP', '0.0.0.0')
    logging.info("Starting doorbell server on %s:%s", ip, port)
    app.run(debug=False, host=ip, port=port, threaded=True)
