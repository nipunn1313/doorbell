import logging
import os
import pprint
import threading
import time

import twilio.twiml

from flask import (
    Flask,
    request,
    redirect,
)
from twilio.rest import TwilioRestClient

client = TwilioRestClient(
    account=os.getenv('TWILIO_API_SID'),
    token=os.getenv('TWILIO_API_TOKEN'),
    request_account=os.getenv('TWILIO_ACCOUNT_SID'),
)

TARGET_PHONES = os.getenv('TARGET_PHONES').split(',')
TWILIO_PHONE = os.getenv('TWILIO_PHONE')

app = Flask(__name__)
open_door_ts = 0.0
open_cond = threading.Condition()

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
        logging.info("Opening door for %s", who)
        resp.message("Opening door")
        with open_cond:
            open_door_ts = time.time()
            open_cond.notify()
    return str(resp)

@app.route("/ring", methods=['GET'])
def ring():
    logging.info("Someone rang the door")
    message = client.messages.create(
        body='Someone rang the doorbell. Respond with "y" to open door',
        to=TARGET_PHONES[0],
        from_=TWILIO_PHONE,
    )
    logging.info("Message(%s) sent. Status: %s", message.sid, message.status)
    return 'ok'

@app.route("/longpoll_open", methods=['GET'])
def longpoll_open():
    poll_end = time.time() + 60.0
    with open_cond:
        while open_door_ts + 10.0 <= time.time() and time.time() <= poll_end:
            open_cond.wait(timeout=poll_end - time.time())

        return 'open' if open_door_ts + 10.0 <= time.time() else 'punt'

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    port = int(os.getenv('PORT'))
    ip = os.getenv('IP', '0.0.0.0')
    logging.info("Starting doorbell server on %s:%s", ip, port)
    app.run(debug=False, host=ip, port=port, threaded=True)
