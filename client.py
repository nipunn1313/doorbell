from __future__ import (
    print_function,
)

import requests
import RPi.GPIO as GPIO
import time

SERVER_URL = 'http://doorbell-to-2580.herokuapp.com'
RING_URL = '%s/ring' % SERVER_URL
POLL_URL = '%s/longpoll_open' % SERVER_URL

PIN_IN = 4
PIN_OUT = 24

def rpio_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_IN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PIN_OUT, GPIO.OUT, initial=0)

def wait_for_ring():
    while GPIO.input(PIN_IN) == 0:
        pass

def open_door():
    GPIO.output(PIN_OUT, 1)
    time.sleep(7)
    GPIO.output(PIN_OUT, 0)

def ring_door():
    print("Ringing door")
    r = requests.get(RING_URL)
    r.raise_for_status()

def should_open():
    print("Waiting to open")
    r = requests.get(POLL_URL)
    if r.text == 'open':
        print("Opening door")
        return True
    else:
        print("Didn't get door-open-response:\n%s" % r.text)
        return False

def main():
    rpio_setup()

    while True:
        wait_for_ring()
        ring_door()
        if should_open():
            open_door()

if __name__ == '__main__':
    main()
