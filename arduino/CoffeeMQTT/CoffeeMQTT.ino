/*
 * Coffee Machine Controller for Arduino Uno R4 WiFi
 * Controls a relay connected to pin 7 for turning the coffee machine on/off
 * Responds to serial commands from a Flask application
 * Reads temperature from DS18B20 sensor (if connected)
 */

 #include <OneWire.h>
 #include <DallasTemperature.h>
 #include <WiFiS3.h>  // WiFi library for Arduino Uno R4 WiFi
 
 // Pin Definitions
 #define RELE_CAFETEIRA 7  // Coffee machine relay
 #define LED_STATUS 2      // Status LED (built-in LED on pin 2)
 #define SENSOR_TEMP 4     // Temperature sensor pin
 
 // Configuration
 #define SERIAL_BAUD 115200
 #define TEMP_CHECK_INTERVAL 2000  // Check temperature every 2 seconds
 
 // System State
 bool cafeteiraLigada = false;     // Coffee machine state
 float temperature = 25.0;         // Default temperature value
 unsigned long lastTempCheck = 0;  // Last temperature reading timestamp
 unsigned long lastHeartbeat = 0;  // Last heartbeat timestamp
 
 // Initialize temperature sensor (if connected)
 OneWire oneWire(SENSOR_TEMP);
 DallasTemperature sensors(&oneWire);
 bool sensorConnected = false;     // Flag to track if sensor is connected
 
 void setup() {
   // Initialize pins
   pinMode(RELE_CAFETEIRA, OUTPUT);
   pinMode(LED_STATUS, OUTPUT);
   
   // Set initial state - coffee machine off
   digitalWrite(RELE_CAFETEIRA, HIGH);  // Mudado de LOW para HIGH
   digitalWrite(LED_STATUS, LOW);
   
   // Start serial communication
   Serial.begin(SERIAL_BAUD);
   while (!Serial && millis() < 3000);  // Wait for serial to connect (with timeout)
   
   // Initialize temperature sensor
   sensors.begin();
   
   // Check if temperature sensor is connected
   sensors.requestTemperatures();
   float tempC = sensors.getTempCByIndex(0);
   if (tempC != DEVICE_DISCONNECTED_C && tempC != -127.00) {
     sensorConnected = true;
     temperature = tempC;
     Serial.println("Temperature sensor detected!");
   } else {
     Serial.println("Temperature sensor not detected. Using simulated values.");
   }
   
   Serial.println("CoffeeAI Control System Ready");
   Serial.println("Available commands:");
   Serial.println("  ping - Check connection");
   Serial.println("  ligar - Turn coffee machine ON");
   Serial.println("  desligar - Turn coffee machine OFF");
   Serial.println("  status - Get system status");
 }
 
 void loop() {
   unsigned long currentMillis = millis();
   
   // Read temperature sensor at regular intervals
   if (currentMillis - lastTempCheck >= TEMP_CHECK_INTERVAL) {
     lastTempCheck = currentMillis;
     if (sensorConnected) {
       sensors.requestTemperatures();
       float tempC = sensors.getTempCByIndex(0);
       if (tempC != DEVICE_DISCONNECTED_C && tempC != -127.00) {
         temperature = tempC;
       }
     }
   }
   
   // Send heartbeat
   if (currentMillis - lastHeartbeat >= 1000) {
     lastHeartbeat = currentMillis;
     // Serial.println("heartbeat");  // Uncomment if your Flask app expects heartbeats
   }
   
   // Check for serial commands
   if (Serial.available()) {
     String command = Serial.readStringUntil('\n');
     command.trim();
     
     // Process commands
     if (command == "ping") {
       Serial.println("pong");
     }
     else if (command == "ligar") {
       handleLigarCommand();
     }
     else if (command == "desligar") {
       handleDesligarCommand();
     }
     else if (command == "status") {
       publishStatus();
     }
   }
   
   // Add a small delay to prevent CPU overload
   delay(10);
 }
 
 void handleLigarCommand() {
  cafeteiraLigada = true;
  digitalWrite(RELE_CAFETEIRA, LOW);  // Mudado de HIGH para LOW
  digitalWrite(LED_STATUS, HIGH);
  Serial.println("ok");
  publishStatus();
}

void handleDesligarCommand() {
  cafeteiraLigada = false;
  digitalWrite(RELE_CAFETEIRA, HIGH);  // Mudado de LOW para HIGH
  digitalWrite(LED_STATUS, LOW);
  Serial.println("ok");
  publishStatus();
}
 
 void publishStatus() {
   // Create JSON-like status message
   Serial.print("{\"status\":\"");
   Serial.print(cafeteiraLigada ? "ligada" : "desligada");
   Serial.print("\",\"system_status\":\"");
   Serial.print(cafeteiraLigada ? "online" : "offline");
   Serial.print("\",\"temperature\":\"");
   Serial.print(temperature);
   Serial.print("\",\"water_level\":\"100");
   Serial.print("\",\"pressure\":\"9.0");
   Serial.println("\"}");
 }