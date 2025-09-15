## Reflex-Game (Flask + WebSockets)
Steuere und spiele ein Reaktionsspiel über den Browser. Optional kann reale Hardware (LED/Buttons) angebunden werden.  
Server: **Python (Flask)**, Echtzeit: **WebSockets (flask-sock)**, Speicherung: **SQLite**.

---

## Hardware

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
sudo apt install -y python3 python3-venv python3-pip
