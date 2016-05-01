import logging
import os
import pprint
import threading

import twilio.twiml

from flask import (
    Flask,
    request,
    redirect,
)
from twilio.rest import TwilioRestClient

ACCOUNT_SID = 'ACbb2ca5675db388166ac0c01d790ad1e5'
AUTH_TOKEN = '1fd4225630787789d968807a5edc53b6'
client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)

TARGET_PHONE = '+17814433967'
#TARGET_PHONE = '+14845540074'
TWILIO_PHONE = '+14156049859'
 
app = Flask(__name__)
should_open = threading.Event()

@app.route("/incoming_text", methods=['GET', 'POST'])
def incoming_text():
    """Handle incoming texts"""
    who = request.values.get('From')
    body = request.values.get('Body', '')
    
    logging.debug('Received message from %s:\n%s', who, body)
    
    if who != TARGET_PHONE:
        logging.info("Text was from a rogue number %s. Ignoring.", who)
        return
    
    resp = twilio.twiml.Response()
    if body in ('y', 'Y', 'yes', 'Yes'):
        logging.info("Opening door for %s", who)
        resp.message("Opening door")
        should_open.set()
    return str(resp)
    
@app.route("/ring", methods=['GET'])
def ring():
    logging.info("Someone rang the door")
    message = client.messages.create(
        body='Someone rang the doorbell. Respond with "y" to open door',
        to=TARGET_PHONE,
        from_=TWILIO_PHONE,
    )
    logging.info("Message(%s) sent. Status: %s", message.sid, message.status)
    return 'ok'
    
@app.route("/longpoll_open", methods=['GET'])
def longpoll_open():
    should_open.wait(timeout=60)
    if should_open.is_set():
        should_open.clear()
        return 'open'
    return 'punt'
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    port = int(os.getenv('PORT'))
    ip = os.getenv('IP')
    logging.info("Starting doorbell server on %s:%s", ip, port)
    app.run(debug=True, host=ip, port=port, threaded=True)