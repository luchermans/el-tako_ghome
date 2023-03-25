""" spesk_driver.py

    Driver for testing: speak the action

    Version Date  Author	Comment
    V1.00 2023-03-25 LH     initial
"""
from win32com.client import Dispatch
TAKO_HOME_API = "http://127.0.0.1:8088/tako-home/api/switch"


speak = Dispatch("SAPI.SpVoice").Speak


def init(tako_home_api):
    global TAKO_HOME_API
    TAKO_HOME_API = tako_home_api


def switch(tako, on):
    txt = f"{tako.replace('.', ' ')} turn {'on' if on else 'off'}"
    speak(txt)


def brightness(tako, percent):
    txt = f"{tako.replace('.', ' ')} brightness set to {percent}"
    speak(txt)


if __name__ == '__main__':        # Test rom command line
    switch('Keuken.LED', 1)
    brightness('Living.TV', 75)
