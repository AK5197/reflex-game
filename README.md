## Reflex-Game (Flask + WebSockets)
Ein IoT-basiertes Reaktionsspiel mit Highscore-System.  
Spieler drücken so schnell wie möglich nach einem Startsignal – die Zeiten werden in einer SQLite-Datenbank gespeichert und live im Browser angezeigt.  

## Motivation
Inspiriert vom F1-Reaktionstest wollten wir ein eigenes Reaktionsspiel bauen, das Technik, IoT und Spielspass verbindet.  

## Architektur
- **Spiellogik (Pico / Pi mit LEDs & Tastern)** → misst Reaktionszeiten  
- **MQTT** → überträgt Daten an den Server  
- **Flask (server.py)** → verarbeitet und speichert in SQLite  
- **REST API & WebSocket** → liefern Daten an den Browser  
- **Weboberfläche** → zeigt Historie und Ranglisten (Overall, P1, P2)  

---

## Hardware
![Steckbrett und Raspberry](https://github.com/AK5197/reflex-game/blob/main/Plan.png)
### Minimal (nur Web)
- Rechner/Raspberry Pi
- Aktueller Browser (Chrome/Firefox/Edge/Safari)

### Optional: Raspberry Pi mit LEDs & Tastern
- **Raspberry Pi** (3B/4/Zero 2 W)
- **LED-Ausgabe** (einfach/WS2812B/NeoPixel-Ring)
- **1–2 Taster** (Start/Stop, Reaktion)
- **Vorwiderstände** für LEDs/Taster

### Optional für adressierbare LEDs (WS2812/NeoPixel)
- **3,3 V → 5 V Pegelwandler** (empfohlen, falls LEDs „glitchen“)
- Nach Adafruit Best Practices:
  - **1000 µF** Kondensator zwischen 5 V/GND
  - **300–500 Ω** Serienwiderstand in der Datenleitung

---

## Features
- Spiel **starten/stoppen**
- **Reaktionszeit messen** und speichern (SQLite `scores.db`)
- **Schwierigkeitsgrad/Intervall** anpassen
- **Live-Feedback** via WebSocket (Startsignal, Treffer, Zeit)
- Optional: **physische Taster/LEDs** via GPIO

---

## Web App
Single Page App (HTML/JS/CSS) mit **Bootstrap** und **jQuery**.  
Steuerung über Buttons/Slider/Farbwahl (falls LEDs), automatische Events ohne separaten „Senden“-Klick. Häufige Events werden gedrosselt, um den Server nicht zu fluten.

---

## Installing

### 1) System vorbereiten
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mosquitto
git clone https://github.com/dein-user/reflex-game.git
cd reflex-game
pip install -r requirements.txt
python3 server.py
```
## API

- `/api/scores?limit=1000` → gesamte Historie  
- `/api/top?limit=10` → Top 10  
- `/api/top?player=P1&limit=10` → Top 10 für Spieler P1  
- `/export.csv` → CSV-Export aller Daten  

## Lizenz

GPL-3.0 (oder MIT, je nach Wahl)

## Credits

- [Flask](https://flask.palletsprojects.com/)  
- [flask-sock](https://flask-sock.readthedocs.io/)  
- [Mosquitto MQTT](https://mosquitto.org/)  
- [SQLite](https://sqlite.org/)


