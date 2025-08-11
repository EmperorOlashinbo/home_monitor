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

# Initialize sensors and LED
try:
    dht_sensor = dht.DHT11(machine.Pin(16))  # DHT11 on GPIO 16 (Pin 21)
except Exception as e:
    print("DHT11 initialization failed:", e)
    dht_sensor = None
adc_photo = machine.ADC(machine.Pin(27))  # Photoresistor on GPIO 27 (Pin 32, ADC1)
tilt = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)  # Tilt switch on GPIO 12 (Pin 16)
led = machine.Pin(13, machine.Pin.OUT)    # Red LED on GPIO 13 (Pin 17)

# Function to connect to Wi-Fi with retries
def connect_wifi():
    """Connect to Wi-Fi with up to 20 seconds wait."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Connecting to Wi-Fi...")
    wlan.connect(SSID, PASSWORD)
    for _ in range(20):  # Wait up to 20 seconds
        if wlan.isconnected():
            print("Connected! IP:", wlan.ifconfig()[0])
            return wlan
        time.sleep(1)
    print("Failed to connect to Wi-Fi.")
    return None

# Sensor reading function
def read_sensors():
    """Read all sensor values with error handling and debounce."""
    try:
        dht_sensor.measure()
        time.sleep(2)  # Settle time
        dht_temp = dht_sensor.temperature()
        dht_hum = dht_sensor.humidity()
    except OSError:
        print("Warning: DHT11 read failed")
        dht_temp, dht_hum = None, None
    light_value = adc_photo.read_u16()
    light_level = (light_value / 65535) * 100
    tilt_state = tilt.value()
    time.sleep(0.1)  # Debounce
    is_tilted = (tilt_state == 0)
    led.value(is_tilted)
    return dht_temp, dht_hum, light_level, is_tilted
