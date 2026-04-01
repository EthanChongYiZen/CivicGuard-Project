# CivicGuard Smart Gate

An AI-powered smart gate access control system that uses real-time sensor data and a local LLM to make automated entry decisions for critical infrastructure.

## Overview

CivicGuard combines an Arduino with an ultrasonic sensor and LDR (light sensor) to detect presence and ambient light conditions. Sensor data is sent over serial to a Python script, which queries a local LLM (via Ollama) to decide whether to grant or deny access. The decision is sent back to the Arduino to control an RGB LED indicator and a servo-operated gate.

## How It Works

```
Arduino (sensors) → Serial → Python AI Agent → Ollama LLM → Decision → Arduino (LED + gate)
```

**Access Logic:**
| Condition | Decision | LED |
|-----------|----------|-----|
| Person detected + Daytime (light > 500) | Grant / Gate Open | 🟢 Green |
| Person detected + Nighttime (light ≤ 500) | Deny / Gate Closed | 🟡 Yellow |
| No person detected | Standby / Gate Closed | 🔴 Red |

## Hardware Requirements

| Component | Pin |
|-----------|-----|
| Ultrasonic Sensor (HC-SR04) | TRIG: 5, ECHO: 4 |
| LDR (Light Sensor) | A0 |
| Servo Motor (gate) | 9 |
| RGB LED | RED: 11, GREEN: 10, BLUE: 6 |

## Tech Stack

- **Arduino** — C++ / Arduino framework, ArduinoJson, Servo library
- **Python 3** — pyserial, ollama
- **LLM** — Llama 3 8B via Ollama (local, runs offline)

## Getting Started

### 1. Arduino Setup

Install the following libraries in the Arduino IDE:
- `ArduinoJson`
- `Servo` (built-in)

Upload `sketch_oct23a.ino` to your Arduino board.

### 2. Python Setup

```bash
pip install pyserial ollama
```

Pull the LLM model:

```bash
ollama pull llama3:8b
```

### 3. Configure Port

In `smart_gate.py`, update the port if needed:

```python
ARDUINO_PORT = "COM3"  # Windows
# ARDUINO_PORT = "/dev/ttyUSB0"  # Linux/Mac
```

### 4. Run

```bash
python smart_gate.py
```

The script will auto-detect available serial ports. Select your Arduino and use the menu to start the system.

## Menu Options

```
[1] Start AI system     — begin real-time monitoring
[2] Test sensors        — run 10 sensor readings
[3] Show logs           — view recent access decisions
[4] Quit
```

## Notes

- Close the Arduino Serial Monitor before running the Python script — both cannot use the same serial port simultaneously
- Ollama must be running in the background (`ollama serve`)
- The LLM runs fully locally; no internet connection required
