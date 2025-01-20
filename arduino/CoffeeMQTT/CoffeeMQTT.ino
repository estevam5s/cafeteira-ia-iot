// #include <WiFi.h>
// #include <PubSubClient.h>
// #include <ArduinoJson.h>
// #include <OneWire.h>
// #include <DallasTemperature.h>

// // Configurações do WiFi
// const char* ssid = "Penelopecharmosa";
// const char* password = "13275274";

// // Configurações MQTT
// const char* mqtt_server = "localhost";
// const int mqtt_port = 1884;
// const char* mqtt_topic_command = "cafeteira/comando";
// const char* mqtt_topic_status = "cafeteira/status";

// // Pinos do ESP32
// const int RELE_AQUECEDOR = 21;  // GPIO 21
// const int RELE_BOMBA = 22;      // GPIO 22
// const int SENSOR_TEMP = 36;     // GPIO 36 (ADC0)
// const int SENSOR_NIVEL = 23;    // GPIO 23
// const int SENSOR_PRESSAO = 39;  // GPIO 39 (ADC3)
// const int LED_STATUS = 2;       // LED built-in do ESP32

// // Constantes
// const long INTERVALO_ENVIO = 1000; // Intervalo de envio de status (1 segundo)

// // Variáveis globais
// float temperatura = 0.0;
// int nivelAgua = 100;
// float pressao = 0.0;
// bool sistemaPronto = false;
// bool sistemaLigado = false;
// unsigned long ultimoEnvio = 0;

// // Objetos WiFi e MQTT
// WiFiClient espClient;
// PubSubClient client(espClient);

// // Buffer para JSON
// StaticJsonDocument<200> doc;
// char buffer[200];

// void setup() {
//   Serial.begin(115200);
//   pinMode(RELE_AQUECEDOR, OUTPUT);
//   pinMode(RELE_BOMBA, OUTPUT);
//   pinMode(LED_STATUS, OUTPUT);
//   pinMode(SENSOR_NIVEL, INPUT);

//   // Inicialmente, tudo desligado
//   digitalWrite(RELE_AQUECEDOR, HIGH);
//   digitalWrite(RELE_BOMBA, HIGH);
//   digitalWrite(LED_STATUS, HIGH);

//   // Conecta ao WiFi
//   conectarWiFi();

//   // Configura MQTT
//   client.setServer(mqtt_server, mqtt_port);
//   client.setCallback(callback);
// }

// void loop() {
//   if (!client.connected()) {
//     reconnectMQTT();
//   }
//   client.loop();

//   // Processa comandos da serial
//   if (Serial.available() > 0) {
//     String comando = Serial.readStringUntil('\n');
//     processarComando(comando);
//   }

//   // Atualiza leituras dos sensores
//   if (sistemaLigado) {
//     lerSensores();
//   }

//   // Envia status periodicamente
//   unsigned long agora = millis();
//   if (agora - ultimoEnvio >= INTERVALO_ENVIO) {
//     enviarStatus();
//     ultimoEnvio = agora;
//   }

//   // Heartbeat para manter conexão
//   if (agora % 5000 == 0) { // A cada 5 segundos
//     enviarHeartbeat();
//   }
// }

// void conectarWiFi() {
//   Serial.println("Conectando ao WiFi...");
//   WiFi.begin(ssid, password);

//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }

//   Serial.println("\nWiFi conectado");
//   Serial.print("IP: ");
//   Serial.println(WiFi.localIP());
// }

// void reconnectMQTT() {
//   while (!client.connected()) {
//     Serial.print("Conectando ao MQTT...");
//     if (client.connect("ArduinoCafeteira")) {
//       client.subscribe(mqtt_topic_command);
//       Serial.println("Conectado!");
//     } else {
//       Serial.print("Falha, rc=");
//       Serial.print(client.state());
//       Serial.println(" tentando novamente em 5 segundos");
//       delay(5000);
//     }
//   }
// }

// void callback(char* topic, byte* payload, unsigned int length) {
//   String mensagem;
//   for (int i = 0; i < length; i++) {
//     mensagem += (char)payload[i];
//   }
//   processarComando(mensagem);
// }

// void processarComando(String comando) {
//   comando.trim();

//   if (comando == "ping") {
//     Serial.println("pong");
//     return;
//   }

//   if (comando == "ligar") {
//     ligarSistema();
//   }
//   else if (comando == "desligar") {
//     desligarSistema();
//   }
// }

// void ligarSistema() {
//   sistemaLigado = true;
//   digitalWrite(RELE_AQUECEDOR, LOW);  // Liga aquecedor
//   digitalWrite(LED_STATUS, LOW);      // Liga LED
//   Serial.println("ok");
// }

// void desligarSistema() {
//   sistemaLigado = false;
//   digitalWrite(RELE_AQUECEDOR, HIGH); // Desliga aquecedor
//   digitalWrite(RELE_BOMBA, HIGH);     // Desliga bomba
//   digitalWrite(LED_STATUS, HIGH);     // Desliga LED
//   temperatura = 0;
//   pressao = 0;
//   Serial.println("ok");
// }

// void lerSensores() {
//   // Simula leitura de temperatura (para teste)
//   if (sistemaLigado) {
//     if (temperatura < 92) {
//       temperatura += 0.5;
//     }
//   }

//   // Lê nível de água
//   nivelAgua = digitalRead(SENSOR_NIVEL) ? 100 : 20;

//   // Simula pressão (para teste)
//   pressao = sistemaLigado ? 9.0 : 0.0;
// }

// void enviarStatus() {
//   doc.clear();
//   doc["status"] = sistemaLigado ? "ligada" : "desligada";
//   doc["temperature"] = String(temperatura, 1);
//   doc["water_level"] = nivelAgua;
//   doc["pressure"] = String(pressao, 1);

//   serializeJson(doc, buffer);
//   client.publish(mqtt_topic_status, buffer);

//   // Também envia pela serial
//   Serial.print("STATUS:");
//   Serial.println(buffer);
// }

// void enviarHeartbeat() {
//   if (sistemaLigado) {
//     client.publish("cafeteira/heartbeat", "alive");
//   }
// }

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

// void loop() {
//     unsigned long currentMillis = millis();

//     // Processa comandos seriais
//     handleSerialCommand();

//     // Verifica conexões
//     if (!state.wifiConnected && (currentMillis - state.lastCommandTime > WIFI_RETRY_INTERVAL)) {
//         connectWiFi();
//     }

//     if (state.wifiConnected && !state.mqttConnected) {
//         connectMQTT();
//     }

//     // Lê sensores
//     if (currentMillis - state.lastSensorRead >= SENSOR_READ_INTERVAL) {
//         readSensors();
//         state.lastSensorRead = currentMillis;
//     }

//     // Publica status
//     if (currentMillis - state.lastHeartbeat >= STATUS_INTERVAL) {
//         publishStatus();
//         state.lastHeartbeat = currentMillis;
//     }

//     // Verifica timeout de comando
//     if (state.cafeteiraLigada &&
//         (currentMillis - state.lastCommandTime > COMMAND_TIMEOUT)) {
//         handleDesligarCommand();
//     }

//     // Mantém conexão MQTT
//     if (state.mqttConnected) {
//         mqttClient.loop();
//     }

//     // Pisca LED se sistema não estiver pronto
//     if (!state.systemReady) {
//         digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
//         delay(500);
//     }
// }

// void loop() {
//     if (Serial.available()) {
//         String command = Serial.readStringUntil('\n');

//         if (command == "ligar") {
//             // Lógica para ligar a cafeteira
//             Serial.println("pong"); // Resposta ao comando
//         } else if (command == "desligar") {
//             // Lógica para desligar a cafeteira
//             Serial.println("pong"); // Resposta ao comando
//         }
//     }
// }

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