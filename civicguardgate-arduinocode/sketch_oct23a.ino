#include <Servo.h>
#include <ArduinoJson.h>

// ============== PIN CONFIGURATION ==============
// Ultrasonic Sensor
#define TRIG_PIN 5
#define ECHO_PIN 4

// LDR (Light Sensor)
#define LDR_PIN A0

// Servo Motor
#define SERVO_PIN 9

// RGB LED
#define RED_PIN 11
#define GREEN_PIN 10
#define BLUE_PIN 6

// ============== GLOBAL VARIABLES ==============
Servo gateServo;
bool systemActive = true;

unsigned long lastSensorSend = 0;
const unsigned long SENSOR_INTERVAL = 1000; // Send data every 1 second (slower = more time for commands)

// ============== SETUP ==============
void setup() {
  Serial.begin(9600);
  
  // Ultrasonic sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  // LDR pin (analog input)
  pinMode(LDR_PIN, INPUT);
  
  // RGB LED pins
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  
  // Servo setup
  gateServo.attach(SERVO_PIN);
  gateServo.write(0); // Start with gate closed
  
  // Initial LED state (red = standby)
  setLED("red");
  
  Serial.println("CivicGuard Smart Gate Ready");
  delay(1000);
}

// ============== HELPER FUNCTIONS ==============

// Measure distance using ultrasonic sensor
float measureDistance() {
  // Clear trigger
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  
  // Send 10us pulse
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Read echo pulse
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  
  // Calculate distance in cm
  float distance = duration * 0.034 / 2;
  
  // Return -1 if no valid reading
  if (distance == 0 || distance > 400) {
    return -1;
  }
  
  return distance;
}

// Read light level from LDR
int readLightLevel() {
  return analogRead(LDR_PIN);
}

// Control RGB LED with visual feedback
void setLED(String color) {
  // Turn off all LEDs first
  digitalWrite(RED_PIN, LOW);
  digitalWrite(GREEN_PIN, LOW);
  digitalWrite(BLUE_PIN, LOW);
  
  // Small delay to ensure clean transition
  delay(10);
  
  if (color == "red") {
    digitalWrite(RED_PIN, HIGH);
    Serial.println("LED: RED");
  } 
  else if (color == "green") {
    digitalWrite(GREEN_PIN, HIGH);
    Serial.println("LED: GREEN");
  } 
  else if (color == "yellow") {
    // Yellow = Red + Green
    digitalWrite(RED_PIN, HIGH);
    digitalWrite(GREEN_PIN, HIGH);
    Serial.println("LED: YELLOW");
  }
}

// Control gate servo with feedback
void controlGate(String action) {
  if (action == "open") {
    gateServo.write(90); // Open position
    Serial.println("GATE: OPEN");
  } 
  else if (action == "closed") {
    gateServo.write(0); // Closed position
    Serial.println("GATE: CLOSED");
  }
  
  delay(100); // Give servo time to start moving
}

// Send sensor data as JSON
void sendSensorData(float distance, int lightLevel) {
  StaticJsonDocument<128> doc;
  
  doc["distance"] = distance;
  doc["light"] = lightLevel;
  doc["person_present"] = (distance >= 0 && distance <= 10) ? 1 : 0;
  doc["time_of_day"] = (lightLevel > 500) ? "day" : "night";
  
  serializeJson(doc, Serial);
  Serial.println(); // Newline terminator
}

// Execute command from AI - IMPROVED VERSION
void executeCommand(const char* json) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, json);
  
  if (err) {
    Serial.print("JSON_ERROR:");
    Serial.println(err.c_str());
    return;
  }
  
  Serial.println("COMMAND_RECEIVED");
  
  // Extract fields
  const char* decision = doc["decision"];
  const char* led = doc["led"];
  const char* gate = doc["gate"];
  
  // Apply LED color (CRITICAL - do this first)
  if (led) {
    setLED(String(led));
  }
  
  // Control gate (do this second)
  if (gate) {
    controlGate(String(gate));
  }
  
  // Print what we did
  if (decision) {
    Serial.print("DECISION: ");
    Serial.println(decision);
  }
  
  Serial.println("CMD_COMPLETE");
}

// Check for incoming commands - IMPROVED VERSION
void checkCommands() {
  // Process ALL available commands before continuing
  while (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    
    if (line.length() == 0) continue;
    
    // Debug: show what we received
    Serial.print("RECEIVED: ");
    Serial.println(line);
    
    // Handle JSON commands
    if (line.startsWith("{")) {
      executeCommand(line.c_str());
    }
  }
}

// ============== MAIN LOOP ==============
void loop() {
  // PRIORITY: Check for commands FIRST and process ALL of them
  checkCommands();
  
  if (!systemActive) {
    delay(200);
    return;
  }
  
  // Send sensor data at regular intervals (slower = more time for commands)
  if (millis() - lastSensorSend >= SENSOR_INTERVAL) {
    // Read sensors
    float distance = measureDistance();
    int lightLevel = readLightLevel();
    
    // Send data
    sendSensorData(distance, lightLevel);
    lastSensorSend = millis();
  }
  
  // Short delay - but spend more time checking for commands
  delay(50);
}