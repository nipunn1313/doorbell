from __future__ import (
    print_function,
)

import requests

SERVER_URL = 'http://doorbell-to-2580.herokuapp.com'
RING_URL = '%s/ring' % SERVER_URL
POLL_URL = '%s/longpoll_open' % SERVER_URL

def ring():
    pass

def main():
    print("Ringing door")
    r = requests.get(RING_URL)
    r.raise_for_status()

    print("Waiting to open")
    r = requests.get(POLL_URL)
    if r.text == 'open':
        print("Opening door")
    else:
        print("Didn't get door-open-response:\n%s" % r.text)

if __name__ == '__main__':
    main()
