#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Configuração dos pinos
const int RELE_CAFETEIRA = 25;
const int LED_STATUS = 2;

// Configurações do WiFi
const char* ssid = "Penelopecharmosa";
const char* password = "13275274";

// Configurações do MQTT
const char* mqtt_server = "192.168.1.107";  // IP atualizado
const int mqtt_port = 1884;
const char* mqtt_topic_command = "cafeteira/comando";
const char* mqtt_topic_status = "cafeteira/status";

// Estado da cafeteira
bool cafeteiraLigada = false;
bool wifiConnected = false;

// Objetos de conexão
WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastWifiCheck = 0;
const long wifiCheckInterval = 5000;

void setup_wifi() {
    // Desconecta se já estiver conectado
    WiFi.disconnect(true);
    delay(1000);
    
    // Configura modo WiFi
    WiFi.mode(WIFI_STA);
    
    Serial.println("\nConectando ao WiFi...");
    Serial.print("SSID: ");
    Serial.println(ssid);
    
    // Lista redes disponíveis antes de tentar conectar
    Serial.println("Redes disponíveis:");
    int n = WiFi.scanNetworks();
    for (int i = 0; i < n; ++i) {
        Serial.printf("%d: %s (%d dBm)\n", i+1, WiFi.SSID(i).c_str(), WiFi.RSSI(i));
    }
    
    WiFi.begin(ssid, password);
    
    // Aguarda conexão com timeout
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
        delay(500);
        Serial.print(".");
        attempts++;
        
        // Mostra status da conexão a cada tentativa
        if (attempts % 5 == 0) {
            Serial.printf("\nStatus WiFi: %d\n", WiFi.status());
        }
    }
    Serial.println("");
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi conectado!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
        Serial.print("Força do sinal: ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");
        digitalWrite(LED_STATUS, HIGH);
        wifiConnected = true;
    } else {
        Serial.println("\nFalha na conexão WiFi");
        Serial.print("Status final: ");
        Serial.println(WiFi.status());
        digitalWrite(LED_STATUS, LOW);
        wifiConnected = false;
    }
}

void handleSerial() {
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        if (command == "ping") {
            Serial.println("pong");
        }
        else if (command == "ligar") {
            cafeteiraLigada = true;
            digitalWrite(RELE_CAFETEIRA, HIGH);
            digitalWrite(LED_STATUS, HIGH);
            Serial.println("ok");
            publishStatus();
        }
        else if (command == "desligar") {
            cafeteiraLigada = false;
            digitalWrite(RELE_CAFETEIRA, LOW);
            digitalWrite(LED_STATUS, LOW);
            Serial.println("ok");
            publishStatus();
        }
        else if (command == "status") {
            Serial.println("\n--- Status do Sistema ---");
            Serial.print("WiFi Status: ");
            Serial.println(WiFi.status());
            Serial.print("WiFi Conectado: ");
            Serial.println(wifiConnected ? "Sim" : "Não");
            if (wifiConnected) {
                Serial.print("IP: ");
                Serial.println(WiFi.localIP());
                Serial.print("RSSI: ");
                Serial.print(WiFi.RSSI());
                Serial.println(" dBm");
            }
            Serial.print("MQTT Conectado: ");
            Serial.println(client.connected() ? "Sim" : "Não");
            Serial.print("Cafeteira: ");
            Serial.println(cafeteiraLigada ? "ligada" : "desligada");
            Serial.println("---------------------");
        }
        else if (command == "scan") {
            Serial.println("\nEscaneando redes WiFi...");
            int n = WiFi.scanNetworks();
            for (int i = 0; i < n; ++i) {
                Serial.printf("%d: %s (%d dBm)\n", i+1, WiFi.SSID(i).c_str(), WiFi.RSSI(i));
            }
        }
        else if (command == "reconnect") {
            Serial.println("Forçando reconexão WiFi...");
            setup_wifi();
        }
    }
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
            publishStatus();
        }
        else if (message == "desligar") {
            cafeteiraLigada = false;
            digitalWrite(RELE_CAFETEIRA, LOW);
            digitalWrite(LED_STATUS, LOW);
            publishStatus();
        }
    }
}

void publishStatus() {
    if (!client.connected() || !wifiConnected) return;
    
    StaticJsonDocument<200> doc;
    doc["status"] = cafeteiraLigada ? "ligada" : "desligada";
    doc["wifi"] = wifiConnected ? "conectado" : "desconectado";
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    
    char buffer[200];
    serializeJson(doc, buffer);
    client.publish(mqtt_topic_status, buffer);
}

void reconnectMQTT() {
    if (!wifiConnected) return;
    
    // Tenta conectar ao MQTT
    if (!client.connected()) {
        Serial.print("Conectando ao MQTT...");
        String clientId = "ESP32Cafeteira-";
        clientId += String(random(0xffff), HEX);
        
        if (client.connect(clientId.c_str())) {
            Serial.println("conectado");
            client.subscribe(mqtt_topic_command);
            publishStatus();
        } else {
            Serial.print("falhou, rc=");
            Serial.print(client.state());
            Serial.println(" tentando novamente em 5 segundos");
        }
    }
}

void setup() {
    // Configuração dos pinos
    pinMode(RELE_CAFETEIRA, OUTPUT);
    pinMode(LED_STATUS, OUTPUT);
    digitalWrite(RELE_CAFETEIRA, LOW);
    digitalWrite(LED_STATUS, LOW);
    
    // Inicia comunicação serial
    Serial.begin(115200);
    delay(2000); // Aguarda inicialização completa
    Serial.println("\nIniciando CoffeeAI Control (ESP32)...");
    
    // Configura WiFi
    setup_wifi();
    
    // Configura MQTT
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback);
}

void loop() {
    // Sempre verifica comandos seriais primeiro
    handleSerial();
    
    // Verifica WiFi periodicamente
    unsigned long currentMillis = millis();
    if (currentMillis - lastWifiCheck >= wifiCheckInterval) {
        lastWifiCheck = currentMillis;
        
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("WiFi desconectado. Reconectando...");
            wifiConnected = false;
            setup_wifi();
        }
    }
    
    // Se WiFi conectado, gerencia MQTT
    if (wifiConnected) {
        if (!client.connected()) {
            reconnectMQTT();
        }
        client.loop();
    }
    
    // Pisca LED se desconectado
    if (!wifiConnected) {
        digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
        delay(500);
    }
}