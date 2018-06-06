#!/usr/bin/python3

import requests
import time

while True:
    time.sleep(30)
    try:
        requests.get(
            'https://taxifishka.com/telegram/taxifishka-check-orders', verify=False)
    except:
        pass
