---
title: Smart Home Indoor Monitor

---

# Smart Home Indoor Monitor
# Tutorial on How to Build a Smart Indoor Monitor

**Ibrahim Olasunbo Ogunbanjo**  
Email: `io222km@student.lnu.se`  
*"This project has been a labor of love and learning!"*

---

## Overview  
I built a Smart Indoor Monitor with a Raspberry Pi Pico WH, tracking temperature, humidity, light levels, and tilt status on a webpage. It sends data to ThingSpeak every 20 seconds and alerts me on Discord when thresholds are crossed (e.g., temp > 30°C). It took me about 2 weeks, including some tough debugging, more details ahead!  

---

## Objective  

### Why I Chose This Topic  
I chose this project because it fits my dorm life perfectly. I often forget to check windows on cold days or notice if rain or snow is fallen, and I wanted a remote monitoring solution. My love for smart home tech drove me to combine sensors with alerts, and I am super exciting!  

### Purpose  
This monitor keeps my indoor environment in check, warning me if the temperature hits 30°C, humidity spikes, light drops below 20%, or if something tilts (like a shelf tipping). The data helps me adjust ventilation or lighting, and alerts keep me informed anywhere via Discord.  

### Expected Insights  
I’m eager to track how temperature and humidity fluctuate daily, how light levels impact my space (maybe my plants or mood!), and if tilt alerts can prevent accidents. I might even optimize my room’s climate or setup based on the trends I see!  

---

## Materials  
*(Here’s the gear I used, all from Electrokit LNU Starter "a course gem!" I’ve added picture placeholders for clarity)*  

| Component          | Purpose                          | Cost    |  
|--------------------|----------------------------------|---------|  
| Raspberry Pi Pico WH | Brain (Wi-Fi enabled)          | 120 kr  |  
| DHT11 Sensor       | Temp & humidity monitoring       | 50 kr   |  
| Photoresistor      | Light level detection            | 30 kr   |  
| Tilt Switch        | Motion/orientation detection     | 30 kr   |  
| LED                | Visual tilt alert                | 20 kr   |  
| Breadboard + Wires | Prototyping                      | 80 kr   |  
| Resistor           | Current limiting/signal stability | 19     |  

**Total Cost**: 349 SEK  

## What the Different Sensors and Components Do - Short Specifications  
- **Pico WH**: Runs MicroPython, GPIO pins, Wi-Fi (802.11n). Specs: 133 MHz dual-core, 264KB RAM.  
- **DHT11**: Digital sensor, temp 0-50°C (±2°C), humidity 20-80% (±5%). Reliable for basics.  
- **Photoresistor**: Varies resistance with light, paired with ADC for 0-100% readings.  
- **Tilt Switch**: HIGH/LOW output based on orientation, great for motion detection.  
- **LED**: 2V, 20mA, with 220Ω resistor for safety.  
- **Wires & Breadboard**: Standard prototyping tools.  


---

## Computer Setup  

### IDE  
- I used **Thonny IDE** its simplicity for MicroPython is a game changer for me.  

### Steps:  
1. **Flashing Firmware**: Downloaded the latest MicroPython firmware, held BOOTSEL, connected the Pico, and dragged the .uf2 file to its drive. Crucial first step!  
2. **Drivers**: No extras needed on Windows and Linux, just enabled USB debugging.  

*A beginner should master the firmware process, it sets everything up!*

---

## Circuit Design  

I connected all sensors and components to the correct GPIO pins on the Raspberry Pi Pico W as shown below:
- DHT11 on GPIO 16.  
- Photoresistor on GPIO 27 with a 220Ω resistor to 3.3V.  
- Tilt switch on GPIO 12 with a pull-up resistor.  
- LED on GPIO 13 with a 220Ω resistor to ground. It’s breadboard based for now, ideal for testing, but I’d use a PCB for production.  

> ![image](https://hackmd.io/_uploads/B17SvLfPgx.png)
> Fig. 1.
  

### Electrical Calculations  
- **LED current**: `3.3V - 2V = 1.3V drop, 1.3V / 220Ω = ~6mA` (well below Pico’s 20mA limit).  
- **Photoresistor calibration**: With a `10kΩ` resistor, the ADC reads `0-3.3V`. I calibrated it so `65535` (max ADC) maps to 100% light, adjusted by trial and error.  
- **Power Consumption**: Pico at `~20mA` idle, sensors add `~5mA—total ~25mA`, fine for USB but a concern for battery use.

---

## Platform & Data Flow  

### Functionality  
I used a local web server (10s refresh), ThingSpeak (20s updates), and Discord alerts. The server runs on the Pico, ThingSpeak graphs data, and Discord pings me.  

### Explain and Elaborate What Made Me Choose This Platform  
I chose ThingSpeak for its free cloud storage and intuitive graphing which is perfect for visualizing trends over months. Discord webhooks were a natural fit since I’m always on it, offering real time alerts without extra apps. Both are free tiers, great for learning, but I compared alternatives: Blynk (paid, more features) and MQTT (local, lower power). ThingSpeak/Discord won for accessibility and my project’s scope. Scaling up, I’d explore paid ThingSpeak or a Raspberry Pi server.  

---

## Code Snippets  
I wrote this in MicroPython on the Pico WH, improving it based on suggestions. Here are key snippets with advanced explanations!  


### Light Level Calculation  
```python
light_value = adc_photo.read_u16()  # 0-65535
light_level = (light_value / 65535) * 100  # Scale to 0-100%
```
- **What I Did**: The photoresistor’s ADC gives a raw `0-65535` value. I scaled it to 0-100% by dividing by 65535 and multiplying by 100, a linear transformation. I used a 10kΩ resistor in a voltage divider to map light intensity, calibrating with room light (~50%) and dark (~5%). This calculation normalizes data for easy interpretation and triggered my low light alert (<20%).

### Sensor Reading with Error Handling
```python
def read_sensors():
    try:
        dht_sensor.measure()
        time.sleep(2)  # Settle time for DHT11
        dht_temp = dht_sensor.temperature()
        dht_hum = dht_sensor.humidity()
    except OSError:
        print("Warning: DHT11 read failed")
        dht_temp, dht_hum = None, None
    light_value = adc_photo.read_u16()
    light_level = (light_value / 65535) * 100
    tilt_state = tilt.value()
    is_tilted = (tilt_state == 0)  # Debounce with 0.1s delay
    time.sleep(0.1)
    return dht_temp, dht_hum, light_level, is_tilted
```
- **What I Did**: I modularized sensor reads into a function, added try/except for DHT11 (Sources 4, 5), and included a 2s settle time. For the tilt switch, I added a 0.1s debounce delay to avoid false triggers, improving reliability.

### ThingSpeak Update  
```python
if wlan.isconnected():
    payload = f"api_key={API_KEY}&field1={dht_temp if dht_temp else 0}&field2={dht_hum if dht_hum else 0}&field3={light_level}&field4={tilt_status}"
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
```
- **What I Did**: This sends data to ThingSpeak every 20s via HTTP GET. The payload formats sensor values into a query string. I added a 3 attempt retry with a 2s delay to handle network drops and calculates reliability by looping until success or exhaustion. The print logs the response (e.g., “1034”) for tracking.

### Terminal Print
```python
print(f"DHT11 Temp: {dht_temp}°C, Light: {light_level:.1f}%, Tilt: {'Tilted' if tilt_status else 'Not Tilted'}, Hum: {dht_hum}% ")
```
- **What I Did**: This prints live data every cycle. I used string formatting to display temp (°C), light (%), tilt status, and humidity (%). The .1f rounds light to one decimal, making it readable. It’s my go-to for quick checks without the webpage.

### Threshold Check and Discord Alert
```python
if wlan.isconnected() and (dht_temp > 30 or light_level < 20 or tilt_status == 1):
    message = f"Alert! Temp: {dht_temp}C, Hum: {dht_hum}%, Light: {light_level:.1f}%, Tilt: {'Tilted' if tilt_status else 'Not Tilted'}"
    payload = '{"content": "%s"}' % message
    try:
        response = urequests.post(DISCORD_WEBHOOK, data=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if response.status_code // 100 == 2:
            print("Sent alert to Discord")
        response.close()
    except Exception as e:
        print("Failed to send Discord alert:", e)
```
- **What I Did**: This checks Wi-Fi and thresholds (30°C, 20% light, tilt=1), chosen based on comfort (hot room) and safety (darkness, falls). I crafted the JSON payload manually after a grueling 400 error fix. The try-except handles network issues, ensuring alerts get through.
- **Setup**: Initialized sensors (DHT11, photoresistor, tilt) and Wi-Fi with network.WLAN.
- **Libraries**: Used dht, machine, network, and urequests.
- ***Advanced Calculation Idea**: I considered smoothing DHT11 data with a running average (e.g., last 5 readings) to reduce noise, but memory limits on the Pico held me back. Formula: sum(readings) / len(readings). I’ll explore this next time!

## Transmitting the Data / Connectivity
### How Is the Data Transmitted
ThingSpeak uses HTTP GET with a query string, Discord uses HTTP POST with JSON.

### All the Different Steps
1. Connect to Wi-Fi.
2. Read sensors.
3. Send to ThingSpeak (20s intervals).
4. Check thresholds and alert Discord if triggered.

### How Often Is the Data Sent?
Every 20s to ThingSpeak, alerts to Discord as needed.

### Which Wireless Protocols Did I Use?
Wi-Fi (802.11n) via Pico WH.

### Which Transport Protocols Were Used?
HTTP for ThingSpeak, webhook for Discord.

### *Elaborate on the Design Choices
Wi-Fi offers good range and ease, though it consumes more power than LoRa (which I tested briefly but found complex). HTTP/webhook suited my simple needs, but MQTT could lower power for battery operated versions. I prioritized reliability and my skill level range is ~30m indoors, and power draw (~25mA) is manageable with USB.

## Presenting the Data
### Describe the Presentation Part
The webpage refreshes every 10 seconds, ThingSpeak plots trends (year-long free storage), and Discord sends alerts. 
> ![Screenshot From 2025-08-09 21-21-33](https://hackmd.io/_uploads/B1PoA4B_ge.png)
Fig. 2.
> ![image](https://hackmd.io/_uploads/ryiV-UGPgx.png)
 Fig. 3


### How Often Is Data Saved in the Database
Every 20s on ThingSpeak.

### *Explain My Choice of Database
ThingSpeak’s free cloud storage was ideal to no local setup, just instant graphing. I compared it to InfluxDB (local, more control) but chose ThingSpeak for its ease and course alignment.

### *Automation/Triggers of the Data
Discord alerts trigger on `temp > 30°C, light < 20%, or tilt = 1`, using conditional logic in the code.



## Finalizing the Design
### Show Final Results of the Project
It’s done! Webpage works, ThingSpeak tracks data, and Discord alerts me. I’m thrilled!

### Pictures
 > ![IMG_9364](https://hackmd.io/_uploads/ryiyo8fPel.png)
 > Fig. 4.
 

### Video Demonstration
> {%youtube https://youtu.be/dy2dOUNjzqs%}

## Conclusion
This was a blast but tough, debugging that Discord JSON error took ages! I could’ve used a PCB for durability or added a battery with power optimization (e.g., sleep mode). The smoothing idea is next on my list. I’ve grown so much and thanks for this journey!