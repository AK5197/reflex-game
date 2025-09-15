# Reaktionsspiel mit zwei Tastern und drei LEDs + MQTT-Highscore
from gpiozero import Button, LED
from time import sleep, time
import random
from signal import pause
import json
import paho.mqtt.client as mqtt

# ==== MQTT Einstellungen ====
MQTT_HOST = "localhost"             # ggf. IP des Raspberry Pi eintragen
MQTT_PORT = 1883
TOPIC = "spiel/reflex/score"        # Topic für Scores

def publish_score(player: str, ms: int):
    """Score als JSON per MQTT senden."""
    try:
        client = mqtt.Client()
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        payload = {"player": player, "ms": ms}
        client.publish(TOPIC, json.dumps(payload), qos=1)
        client.disconnect()
    except Exception as e:
        print("MQTT publish failed:", e)

# ==== LEDs ====
led_1 = LED(17)   # rot (Spieler 1 gewinnt)
led_2 = LED(10)   # gelb (Spieler 2 gewinnt)
led_3 = LED(9)    # grün (Startsignal)

# ==== Taster (gegen GND) ====
btn_1 = Button(27, bounce_time=0.05)
btn_2 = Button(22, bounce_time=0.05)

# Zeitpunkt, an dem grün eingeschaltet wurde
start_ts = None

def pressed_btn_1():
    global start_ts
    # Wenn Spieler 1 schon gewonnen hat: Neustart per Tastendruck
    if led_1.is_lit:
        start_game()
        return

    # Gültiger Treffer nur wenn grün leuchtet
    if led_3.is_lit and start_ts is not None:
        reaction_ms = int((time() - start_ts) * 1000)
        led_1.on()
        led_3.off()
        publish_score("P1", reaction_ms)
        print(f"Spieler 1: {reaction_ms} ms")

def pressed_btn_2():
    global start_ts
    if led_2.is_lit:
        start_game()
        return

    if led_3.is_lit and start_ts is not None:
        reaction_ms = int((time() - start_ts) * 1000)
        led_2.on()
        led_3.off()
        publish_score("P2", reaction_ms)
        print(f"Spieler 2: {reaction_ms} ms")

def start_game():
    """Alles zurücksetzen und nach 5–10 s Startsignal geben."""
    global start_ts
    # Alles aus
    led_1.off()
    led_2.off()
    led_3.off()
    start_ts = None

    # Zufällige Wartezeit 5–10 s
    wait_s = random.uniform(5, 10)
    sleep(wait_s)

    # Startsignal und Startzeit merken
    led_3.on()
    start_ts = time()

# Callbacks setzen
btn_1.when_pressed = pressed_btn_1
btn_2.when_pressed = pressed_btn_2

# Spiel starten und Programm lebendig halten
start_game()
pause()
