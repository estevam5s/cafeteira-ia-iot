#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include <Preferences.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// Pinos do ESP32
#define RELE_CAFETEIRA 25  // GPIO25 para relé da cafeteira
#define LED_STATUS 2       // LED interno do ESP32
#define SENSOR_TEMP 4      // GPIO4 para sensor de temperatura
#define SENSOR_NIVEL 34    // GPIO34 para sensor de nível (ADC)
#define SENSOR_PRESSAO 35  // GPIO35 para sensor de pressão (ADC)

// Debug
#define DEBUG true
#define SERIAL_BAUD 115200

// Configuração de sensores
OneWire oneWire(SENSOR_TEMP);
DallasTemperature sensors(&oneWire);

// Estrutura para configurações
struct Config {
  char wifi_ssid[32];
  char wifi_password[32];
  char mqtt_server[32];
  int mqtt_port;
  bool configured;
};

// Estrutura para estado do sistema
struct SystemState {
  bool cafeteiraLigada;
  bool wifiConnected;
  bool mqttConnected;
  bool systemReady;
  float temperature;
  int waterLevel;
  float pressure;
  String lastError;
  unsigned long lastCommandTime;
  unsigned long lastSensorRead;
  unsigned long lastHeartbeat;
  unsigned long startTime;
};

// Constantes
const unsigned long SENSOR_READ_INTERVAL = 2000;  // 2 segundos
const unsigned long HEARTBEAT_INTERVAL = 1000;    // 1 segundo
const unsigned long STATUS_INTERVAL = 5000;       // 5 segundos
const unsigned long COMMAND_TIMEOUT = 300000;     // 5 minutos
const unsigned long WIFI_RETRY_INTERVAL = 30000;  // 30 segundos
const int MAX_WIFI_ATTEMPTS = 10;
const float TEMP_MIN = 20.0;
const float TEMP_MAX = 96.0;
const int WATER_MIN = 20;
const float PRESSURE_MIN = 8.0;
const float PRESSURE_MAX = 12.0;

// Variáveis globais
Config config;
SystemState state;
Preferences preferences;
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Tópicos MQTT
const char* MQTT_TOPIC_COMMAND = "cafeteira/comando";
const char* MQTT_TOPIC_STATUS = "cafeteira/status";
const char* MQTT_TOPIC_HEARTBEAT = "cafeteira/heartbeat";

// Funções de utilidade
void debugPrint(const char* message) {
  if (DEBUG) {
    Serial.println(message);
  }
}

void debugPrintf(const char* format, ...) {
  if (DEBUG) {
    char buffer[256];
    va_list args;
    va_start(args, format);
    vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);
    Serial.print(buffer);
  }
}

// Funções de configuração
void loadConfig() {
  preferences.begin("coffee", true);
  preferences.getBytes("config", &config, sizeof(config));
  preferences.end();

  if (!config.configured) {
    strcpy(config.wifi_ssid, "SuaRedeWiFi");
    strcpy(config.wifi_password, "SuaSenhaWiFi");
    strcpy(config.mqtt_server, "localhost");
    config.mqtt_port = 1884;
    config.configured = false;
  }
}

void saveConfig() {
  preferences.begin("coffee", false);
  preferences.putBytes("config", &config, sizeof(config));
  preferences.end();
}

// Funções de sensor
void readSensors() {
  // Leitura de temperatura
  sensors.requestTemperatures();
  state.temperature = sensors.getTempCByIndex(0);
  if (state.temperature == DEVICE_DISCONNECTED_C) {
    state.temperature = 25.0;  // Valor padrão se sensor falhar
  }

  // Leitura do nível de água (simulado com ADC)
  int rawWater = analogRead(SENSOR_NIVEL);
  state.waterLevel = map(rawWater, 0, 4095, 0, 100);

  // Leitura de pressão (simulado com ADC)
  int rawPressure = analogRead(SENSOR_PRESSAO);
  state.pressure = map(rawPressure, 0, 4095, 0, 15);
}

// Funções de comunicação
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  debugPrint("Conectando ao WiFi...");
  WiFi.begin(config.wifi_ssid, config.wifi_password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < MAX_WIFI_ATTEMPTS) {
    digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    state.wifiConnected = true;
    debugPrint("\nWiFi conectado!");
    debugPrintf("IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    state.wifiConnected = false;
    state.lastError = "Falha na conexão WiFi";
  }
}

void connectMQTT() {
  if (!state.wifiConnected || mqttClient.connected()) return;

  debugPrint("Conectando ao MQTT...");
  String clientId = "ESP32Coffee-";
  clientId += String(random(0xffff), HEX);

  if (mqttClient.connect(clientId.c_str())) {
    state.mqttConnected = true;
    mqttClient.subscribe(MQTT_TOPIC_COMMAND);
    debugPrint("MQTT Conectado!");
  } else {
    state.mqttConnected = false;
    state.lastError = "Falha MQTT: " + String(mqttClient.state());
  }
}

void publishStatus() {
  StaticJsonDocument<512> doc;
  char buffer[512];

  doc["status"] = state.cafeteiraLigada ? "ligada" : "desligada";
  doc["system_status"] = state.systemReady ? "online" : "offline";
  doc["temperature"] = state.temperature;
  doc["water_level"] = state.waterLevel;
  doc["pressure"] = state.pressure;
  doc["last_error"] = state.lastError;
  doc["uptime"] = (millis() - state.startTime) / 1000;

  serializeJson(doc, buffer);

  // Publica no MQTT se conectado
  if (state.mqttConnected) {
    mqttClient.publish(MQTT_TOPIC_STATUS, buffer);
  }

  // Sempre envia pela serial
  Serial.println(buffer);
}

// Callback MQTT
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  debugPrintf("Mensagem MQTT [%s]: %s\n", topic, message.c_str());

  if (message == "ligar") {
    handleLigarCommand();
  } else if (message == "desligar") {
    handleDesligarCommand();
  }
}

// Handlers de comando
void handleSerialCommand() {
  if (!Serial.available()) return;

  String command = Serial.readStringUntil('\n');
  command.trim();

  debugPrintf("Comando Serial: %s\n", command.c_str());

  if (command == "ping") {
    Serial.println("pong");
  } else if (command == "ligar") {
    handleLigarCommand();
  } else if (command == "desligar") {
    handleDesligarCommand();
  } else if (command == "status") {
    publishStatus();
  } else if (command == "config") {
    handleConfigCommand();
  }
}

void handleLigarCommand() {
  if (!state.systemReady) {
    Serial.println("error:sistema_nao_pronto");
    return;
  }

  if (state.temperature > TEMP_MAX) {
    Serial.println("error:temperatura_alta");
    return;
  }

  if (state.waterLevel < WATER_MIN) {
    Serial.println("error:nivel_agua_baixo");
    return;
  }

  state.cafeteiraLigada = true;
  digitalWrite(RELE_CAFETEIRA, HIGH);
  digitalWrite(LED_STATUS, HIGH);
  state.lastCommandTime = millis();
  Serial.println("ok");
  publishStatus();
}

void handleDesligarCommand() {
  state.cafeteiraLigada = false;
  digitalWrite(RELE_CAFETEIRA, LOW);
  digitalWrite(LED_STATUS, LOW);
  Serial.println("ok");
  publishStatus();
}

void handleConfigCommand() {
  Serial.setTimeout(30000);

  Serial.println("Digite o SSID do WiFi:");
  String ssid = Serial.readStringUntil('\n');
  ssid.trim();

  Serial.println("Digite a senha do WiFi:");
  String pass = Serial.readStringUntil('\n');
  pass.trim();

  Serial.println("Digite o IP do servidor MQTT:");
  String mqtt = Serial.readStringUntil('\n');
  mqtt.trim();

  Serial.println("Digite a porta MQTT (padrão 1884):");
  String port = Serial.readStringUntil('\n');
  port.trim();

  if (ssid.length() > 0 && pass.length() > 0) {
    ssid.toCharArray(config.wifi_ssid, sizeof(config.wifi_ssid));
    pass.toCharArray(config.wifi_password, sizeof(config.wifi_password));
    mqtt.toCharArray(config.mqtt_server, sizeof(config.mqtt_server));
    config.mqtt_port = port.toInt() > 0 ? port.toInt() : 1884;
    config.configured = true;

    saveConfig();
    Serial.println("Configurações salvas! Reiniciando...");
    delay(1000);
    ESP.restart();
  } else {
    Serial.println("Configuração cancelada");
  }

  Serial.setTimeout(1000);
}

// Setup e Loop principais
void setup() {
  // Inicialização de pinos
  pinMode(RELE_CAFETEIRA, OUTPUT);
  pinMode(LED_STATUS, OUTPUT);
  digitalWrite(RELE_CAFETEIRA, LOW);
  digitalWrite(LED_STATUS, LOW);

  // Inicialização de sensores
  sensors.begin();

  // Inicialização da comunicação serial
  Serial.begin(SERIAL_BAUD);
  Serial.setTimeout(1000);

  // Inicialização do estado
  state = {
    false,    // cafeteiraLigada
    false,    // wifiConnected
    false,    // mqttConnected
    false,    // systemReady
    25.0,     // temperature
    100,      // waterLevel
    9.0,      // pressure
    "",       // lastError
    0,        // lastCommandTime
    0,        // lastSensorRead
    0,        // lastHeartbeat
    millis()  // startTime
  };

  // Carrega configurações
  loadConfig();

  // Configura callbacks MQTT
  mqttClient.setServer(config.mqtt_server, config.mqtt_port);
  mqttClient.setCallback(mqttCallback);

  debugPrint("\n=== CoffeeAI Control v2.1 ===\n");

  // Sistema pronto
  state.systemReady = true;
  debugPrint("Sistema Inicializado!");
}

unsigned long lastMillis = 0;
const long interval = 1000;

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastMillis >= interval) {
    lastMillis = currentMillis;

    // Tarefas periódicas aqui (se necessário)
  }

  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');

    if (command == "ping") {
      Serial.println("pong");
    }
  }
}

// O arduino deve estar conectado no porta /dev/ttyS4