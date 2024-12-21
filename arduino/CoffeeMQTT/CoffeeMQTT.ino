#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// Configurações do WiFi
const char* ssid = "seu_wifi";
const char* password = "sua_senha";

// Configurações do MQTT
const char* mqtt_server = "localhost";  // Endereço do seu broker MQTT
const int mqtt_port = 1883;
const char* mqtt_topic_command = "cafeteira/comando";
const char* mqtt_topic_status = "cafeteira/status";

// Configuração dos pinos
const int RELE_CAFETEIRA = D1;     // Pino do relé
const int SENSOR_TEMP = D2;        // Pino do sensor DS18B20
const int SENSOR_NIVEL = D3;       // Pino do sensor de nível d'água
const int LED_STATUS = LED_BUILTIN; // LED de status

// Configuração dos sensores
OneWire oneWire(SENSOR_TEMP);
DallasTemperature sensors(&oneWire);

// Estado da cafeteira
bool cafeteiraLigada = false;
float temperatura = 0.0;
int nivelAgua = 0;
unsigned long lastUpdate = 0;
const long updateInterval = 2000; // Intervalo de atualização (2 segundos)

// Objetos de conexão
WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
    delay(10);
    Serial.println("\nConectando ao WiFi...");
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
    }

    digitalWrite(LED_STATUS, HIGH);
    Serial.println("\nWiFi conectado");
    Serial.println("IP: " + WiFi.localIP().toString());
}

void publishStatus() {
    StaticJsonDocument<256> doc;
    char buffer[256];

    doc["status"] = cafeteiraLigada ? "ligada" : "desligada";
    doc["temperature"] = String(temperatura, 1);
    doc["water_level"] = nivelAgua;
    doc["timestamp"] = millis();

    serializeJson(doc, buffer);
    client.publish(mqtt_topic_status, buffer);
    Serial.println("Status publicado: " + String(buffer));
}

void callback(char* topic, byte* payload, unsigned int length) {
    String message = "";
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    
    Serial.println("Mensagem recebida [" + String(topic) + "]: " + message);

    if (String(topic) == mqtt_topic_command) {
        if (message == "ligar") {
            cafeteiraLigada = true;
            digitalWrite(RELE_CAFETEIRA, HIGH);
            digitalWrite(LED_STATUS, HIGH);
        }
        else if (message == "desligar") {
            cafeteiraLigada = false;
            digitalWrite(RELE_CAFETEIRA, LOW);
            digitalWrite(LED_STATUS, LOW);
        }
        publishStatus();
    }
}

void reconnect() {
    while (!client.connected()) {
        Serial.print("Conectando ao MQTT...");
        String clientId = "ArduinoCafeteira-";
        clientId += String(random(0xffff), HEX);
        
        if (client.connect(clientId.c_str())) {
            Serial.println("conectado");
            client.subscribe(mqtt_topic_command);
            publishStatus();
        } else {
            Serial.print("falhou, rc=");
            Serial.print(client.state());
            Serial.println(" tentando novamente em 5 segundos");
            delay(5000);
        }
    }
}

void readSensors() {
    // Leitura da temperatura
    sensors.requestTemperatures();
    float tempC = sensors.getTempCByIndex(0);
    if (tempC != DEVICE_DISCONNECTED_C) {
        temperatura = tempC;
    }

    // Leitura do nível de água
    nivelAgua = map(analogRead(SENSOR_NIVEL), 0, 1023, 0, 100);
}

void setup() {
    pinMode(RELE_CAFETEIRA, OUTPUT);
    pinMode(LED_STATUS, OUTPUT);
    digitalWrite(RELE_CAFETEIRA, LOW);
    digitalWrite(LED_STATUS, LOW);
    
    Serial.begin(115200);
    Serial.println("\nIniciando CoffeeAI Control...");
    
    // Inicializar sensores
    sensors.begin();
    
    setup_wifi();
    
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    unsigned long currentMillis = millis();
    if (currentMillis - lastUpdate >= updateInterval) {
        lastUpdate = currentMillis;
        readSensors();
        publishStatus();
    }
}