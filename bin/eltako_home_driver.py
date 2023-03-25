""" el-tako_driver.py

    Driver for el-tako_home https://github.com/luchermans/el-tako_home
    FAM14: FTS14EM, FUD14, FSR14  FSB14

    Version Date  Author	Comment
    V1.00 2023-03-25 LH     initial
"""

import requests
TAKO_HOME_API = "http://127.0.0.1:8088/tako-home/api/switch"


def init(tako_home_api):
    global TAKO_HOME_API
    TAKO_HOME_API = tako_home_api


def switch(tako, on):
    jos = {tako: "turn_on" if on else "turn_off"}
    try:
        r = requests.post(TAKO_HOME_API, json=jos)
        r.raise_for_status()
    except Exception as e:
        print(e)


def brightness(tako, data):
    pass    # curently not implemented


if __name__ == '__main__':        # Test rom command line
    switch('Keuken.LED', 1)
    brightness('Living.TV', 75)
