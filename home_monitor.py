import dht
import machine
import network
import urequests
import time
import socket
import ujson

# Project: Smart Indoor Monitor
# Description: Monitors temperature, humidity, light, and tilt using a Pico WH,
#              serves data via a web page, sends updates to ThingSpeak, and
#              alerts Discord on threshold breaches.
# Usage: Connect sensors (DHT11 on GPIO 16, Photoresistor on GPIO 27, Tilt on GPIO 12,
#        LED on GPIO 13), set Wi-Fi credentials, and access via the displayed IP.

try:
    from config import SSID, PASSWORD, THINGSPEAK_API_KEY, THINGSPEAK_URL, DISCORD_WEBHOOK_URL, TEMP_THRESHOLD, HUMIDITY_THRESHOLD, LIGHT_THRESHOLD
except ImportError:
    print("config.py not found, using defaults")
    
