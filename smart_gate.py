#!/usr/bin/env python3
"""
CivicGuard Smart Gate Access Control - Simplified Version
"""

import serial
import json
import time
import sys
from datetime import datetime
import ollama
import threading

# ==================== CONFIGURATION ====================
ARDUINO_PORT = "COM3"  # Change to your port
BAUD_RATE = 9600
LLM_MODEL = "llama3:8b"

# ==================== SMART GATE AI ====================
class SmartGateAI:
    
    SYSTEM_PROMPT = """You are CivicGuard security AI for critical infrastructure.

RULES (apply in order):
1. Person at gate (distance 0-10cm) + Daytime (light>500):
   → {"decision":"grant","led":"green","gate":"open","reason":"Normal business hours","threat_level":"none"}

2. Person at gate (distance 0-10cm) + Nighttime (light<500):
   → {"decision":"deny","led":"yellow","gate":"closed","reason":"After-hours access requires verification","threat_level":"medium"}

3. No person (distance >10cm):
   → {"decision":"standby","led":"red","gate":"closed","reason":"Monitoring mode","threat_level":"none"}

Respond with ONLY the JSON object. No extra text."""

    def __init__(self, port, model=LLM_MODEL):
        self.port = port
        self.model = model
        self.arduino = None
        self.running = False
        self.ai_active = False
        self.decision_log = []
        
        print("\n" + "="*60)
        print("   🏢 CivicGuard Smart Gate System")
        print("="*60 + "\n")
        
        self._connect_arduino()
        self._test_llm()
    
    def _connect_arduino(self):
        """Connect to Arduino"""
        try:
            self.arduino = serial.Serial(self.port, BAUD_RATE, timeout=2)
            time.sleep(2)
            print(f"✓ Connected to Arduino on {self.port}")
            
            # Flush any old data
            self.arduino.reset_input_buffer()
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("\n💡 Tips:")
            print("  - Close Arduino Serial Monitor")
            print("  - Check port name (Device Manager on Windows)")
            print("  - Try different USB cable")
            sys.exit(1)
    
    def _test_llm(self):
        """Test LLM"""
        try:
            print(f"⏳ Testing {self.model}...")
            start = time.time()
            
            ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": "Say OK"}]
            )
            
            elapsed = time.time() - start
            print(f"✓ LLM ready ({elapsed:.1f}s)\n")
            
        except Exception as e:
            print(f"❌ LLM error: {e}")
            print(f"Run: ollama pull {self.model}")
            sys.exit(1)
    
    def _read_sensor_data(self):
        """Read sensor data from Arduino"""
        try:
            # Clear old data first
            self.arduino.reset_input_buffer() # type: ignore
            
            # Wait for fresh data
            timeout = time.time() + 3  # 3 second timeout
            while time.time() < timeout:
                if self.arduino.in_waiting > 0: # type: ignore
                    line = self.arduino.readline().decode('utf-8', errors='ignore').strip() # type: ignore
                    
                    # Skip non-JSON lines
                    if not line.startswith("{"):
                        continue
                    
                    # Parse JSON
                    data = json.loads(line)
                    
                    # Validate data has required fields
                    if 'distance' in data and 'light' in data:
                        return data
                
                time.sleep(0.1)
            
            print("⚠️  Timeout waiting for sensor data")
            return None
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON error: {line}") # type: ignore
            return None
        except Exception as e:
            print(f"⚠️  Read error: {e}")
            return None
    
    def _send_command(self, cmd_dict):
        """Send command to Arduino"""
        try:
            cmd = json.dumps(cmd_dict) + "\n"
            self.arduino.write(cmd.encode()) # type: ignore
            time.sleep(0.1)  # Give Arduino time to process
        except Exception as e:
            print(f"❌ Send error: {e}")
    
    def _query_llm(self, sensor_data):
        """Get AI decision"""
        # Simple prompt
        prompt = f"""distance={sensor_data['distance']:.0f}cm, light={sensor_data['light']}, person_present={sensor_data['person_present']}, time={sensor_data['time_of_day']}"""
        
        try:
            print(f"🤖 Analyzing: {prompt}")
            start = time.time()
            
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.1,
                    "num_predict": 80
                }
            )
            
            elapsed = time.time() - start
            result = response['message']['content'].strip()
            
            # Extract JSON
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            
            if json_start >= 0:
                decision = json.loads(result[json_start:json_end])
                decision['response_time'] = f"{elapsed:.1f}s"
                return decision
            else:
                print(f"⚠️  No JSON in response: {result}")
                return None
                
        except Exception as e:
            print(f"❌ LLM error: {e}")
            return None
    
    def _display_decision(self, sensors, decision):
        """Display decision"""
        print("\n" + "="*60)
        print(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        print(f"📊 Distance: {sensors['distance']:.0f}cm | Light: {sensors['light']}")
        print(f"   Person: {'YES' if sensors['person_present'] else 'NO'} | Time: {sensors['time_of_day'].upper()}")
        print(f"🚦 Decision: {decision['decision'].upper()}")
        print(f"   LED: {decision['led'].upper()} | Gate: {decision['gate'].upper()}")
        print(f"💭 {decision.get('reason', 'N/A')}")
        print(f"⏱️  Response: {decision.get('response_time', 'N/A')}")
        print("="*60 + "\n")
        
        # Log it
        self.decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "sensors": sensors,
            "decision": decision
        })
    
    def start(self):
        """Start AI monitoring"""
        self.ai_active = True
        self.running = True
        
        print("🧠 AI System ACTIVE")
        print("💡 Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                # Read sensors
                sensor_data = self._read_sensor_data()
                
                if not sensor_data:
                    continue
                
                # Get AI decision
                decision = self._query_llm(sensor_data)
                
                if decision:
                    # Send to Arduino
                    self._send_command(decision)
                    
                    # Display result
                    self._display_decision(sensor_data, decision)
                
                # Wait before next reading
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopping AI system...")
            self.stop()
    
    def stop(self):
        """Stop system"""
        self.running = False
        self.ai_active = False
        
        if self.arduino and self.arduino.is_open:
            # Reset to safe state
            self._send_command({
                "led": "red",
                "gate": "closed"
            })
            self.arduino.close()
        
        print("✓ System stopped\n")
    
    def show_logs(self):
        """Show recent logs"""
        if not self.decision_log:
            print("No decisions logged yet.\n")
            return
        
        print("\n📋 Recent Decisions:\n")
        for log in self.decision_log[-5:]:
            print(f"⏰ {log['timestamp']}")
            print(f"   {log['sensors']['distance']:.0f}cm | Light {log['sensors']['light']}")
            print(f"   {log['decision']['decision'].upper()} - {log['decision'].get('reason')}\n")
    
    def test_sensors(self):
        """Test sensor readings"""
        print("🔍 Testing sensors (10 readings)...\n")
        
        for i in range(10):
            data = self._read_sensor_data()
            if data:
                print(f"Reading {i+1}:")
                print(f"  Distance: {data['distance']:.1f}cm")
                print(f"  Light: {data['light']}")
                print(f"  Person: {'YES' if data['person_present'] else 'NO'}")
                print(f"  Time: {data['time_of_day']}\n")
            else:
                print(f"Reading {i+1}: FAILED\n")
            
            time.sleep(1)

# ==================== PORT DETECTION ====================
def find_port():
    """Find Arduino port"""
    import serial.tools.list_ports
    
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        return input("Enter port manually (e.g., COM3): ").strip()
    
    print("Available ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device} - {p.description}")
    
    if len(ports) == 1:
        print(f"\n✓ Using {ports[0].device}\n")
        return ports[0].device
    
    choice = input(f"\nSelect [0-{len(ports)-1}] or Enter for 0: ").strip()
    idx = int(choice) if choice else 0
    return ports[idx].device

# ==================== MAIN ====================
def main():
    """Main program"""
    
    # Find port
    port = find_port()
    
    # Create agent
    agent = SmartGateAI(port)
    
    # Main menu
    while True:
        print("="*60)
        print("Commands:")
        print("  [1] Start AI system")
        print("  [2] Test sensors")
        print("  [3] Show logs")
        print("  [4] Quit")
        print("="*60)
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            agent.start()
        elif choice == "2":
            agent.test_sensors()
        elif choice == "3":
            agent.show_logs()
        elif choice == "4":
            agent.stop()
            print("Goodbye!\n")
            break
        else:
            print("Invalid choice\n")

if __name__ == "__main__":
    main()