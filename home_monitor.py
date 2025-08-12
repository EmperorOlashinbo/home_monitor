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

# Web server function
def start_web_server(wlan):
    """Start a web server to display sensor data, refreshing every 10 seconds."""
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server started on http://", wlan.ifconfig()[0])
    while True:
        cl, addr = s.accept()
        cl_file = cl.makefile('rwb', 0)
        request = cl_file.readline().decode('utf-8').strip()
        if request.startswith('GET / '):
            dht_temp, dht_hum, light_level, is_tilted = read_sensors()
            css = """
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f0f4f8;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .container {
                    background-color: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    width: 300px;
                }
                h1 {
                    color: #2c3e50;
                    font-size: 24px;
                    margin-bottom: 20px;
                }
                p {
                    color: #34495e;
                    font-size: 16px;
                    margin: 10px 0;
                }
                .alert {
                    color: #e74c3c;
                    font-weight: bold;
                }
            </style>
            """
            html_body = """
            <div class="container">
                <h1>Smart Indoor Monitor</h1>
                <p>Temperature (DHT11): {temp}°C</p>
                <p>Humidity (DHT11): {hum}%</p>
                <p>Light Level: {light:.1f}%</p>
                <p>Tilt Status: {tilt}</p>
            </div>
            """
            html = """<!DOCTYPE html>
<html>
<head>
    <title>Smart Indoor Monitor</title>
    <meta http-equiv="refresh" content="10">
    {css}
</head>
<body>
    {body}
</body>
</html>""".format(css=css, body=html_body.format(temp=dht_temp if dht_temp is not None else "N/A",
                                                hum=dht_hum if dht_hum is not None else "N/A",
                                                light=light_level,
                                                tilt='<span class="alert">Tilted</span>' if is_tilted else "Not Tilted"))
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html
            cl.send(response.encode())
        cl.close()

# Connect to Wi-Fi
wlan = connect_wifi()

if wlan is not None and wlan.isconnected():
    # Start web server in a separate thread with wlan reference
    import _thread
    _thread.start_new_thread(start_web_server, (wlan,))
else:
    print("No Wi-Fi, web server not started")

while True:
    try:
        # Read sensors
        dht_temp, dht_hum, light_level, is_tilted = read_sensors()

        # Print sensor readings
        print(f"DHT11 Temp: {dht_temp}°C, "
              f"Light: {light_level:.1f}%, Tilt: {'Tilted' if is_tilted else 'Not Tilted'}, "
              f"Hum: {dht_hum}% ")

        # Send data to ThingSpeak with retry if connected
        if wlan is not None and wlan.isconnected():
            payload = (f"api_key={THINGSPEAK_API_KEY}&field1={dht_temp if dht_temp is not None else 0}&"
                       f"field2={dht_hum if dht_hum is not None else 0}&field3={light_level}&"
                       f"field4={1 if is_tilted else 0}")
            for attempt in range(3):  # Retry 3 times
                try:
                    response = urequests.get(THINGSPEAK_URL + "?" + payload, timeout=10)
                    print("ThingSpeak response:", response.text)
                    response.close()
                    break
                except Exception as e:
                    print(f"ThingSpeak failed (Attempt {attempt + 1}/3): {e}")
                    if attempt == 2:
                        raise
                    time.sleep(2)
        else:
            print("No Wi-Fi connection, skipping ThingSpeak update")

        # Send Discord alert if thresholds are exceeded and Wi-Fi is available
        if wlan is not None and wlan.isconnected() and (dht_temp > TEMP_THRESHOLD if dht_temp is not None else False or
                                                       dht_hum > HUMIDITY_THRESHOLD if dht_hum is not None else False or
                                                       light_level < LIGHT_THRESHOLD or is_tilted):
            message = f"Alert! DHT11 Temp: {dht_temp if dht_temp is not None else 'N/A'}C, Hum: {dht_hum if dht_hum is not None else 'N/A'}%, Light: {light_level:.1f}%, Tilt: {'Tilted' if is_tilted else 'Not Tilted'}"
            payload = ujson.dumps({"content": message})  # Use ujson for robust JSON
            try:
                response = urequests.post(DISCORD_WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json"}, timeout=10)
                response_text = response.text if response else "No response"
                if response.status_code // 100 == 2:  # Success (200-299)
                    print("Sent alert to Discord")
                else:
                    print(f"Discord alert failed: Status {response.status_code}, Response: {response_text}")
                response.close()
            except Exception as e:
                print("Failed to send Discord alert:", e)

        time.sleep(20)  # ThingSpeak free tier requires 15+ seconds between updates

    except OSError as e:
        print("Sensor/Network Error:", e)
        for _ in range(3):  # Flash LED 3 times to indicate error
            led.value(1)
            time.sleep(0.5)
            led.value(0)
            time.sleep(0.5)
        time.sleep(5)
    except Exception as e:
        print("Unexpected Error:", e)
        for _ in range(3):  # Flash LED 3 times for unexpected errors
            led.value(1)
            time.sleep(0.5)
            led.value(0)
            time.sleep(0.5)
        time.sleep(5)
