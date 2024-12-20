#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Configurações do WiFi
const char* ssid = "Penelopecharmosa";
const char* password = "13275274";

// Configurações do MQTT
const char* mqtt_server = "seu_broker_mqtt";
const int mqtt_port = 1883;
const char* mqtt_topic_command = "cafeteira/comando";
const char* mqtt_topic_status = "cafeteira/status";

// Pinos
const int RELE_CAFETEIRA = D1;
const int SENSOR_TEMP = A0;
const int SENSOR_NIVEL = D2;

// Estado da cafeteira
bool cafeteiraLigada = false;
float temperatura = 0;
int nivelAgua = 0;

// Objetos de conexão
WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("IP: ");
  Serial.println(WiFi.localIP());
}

void publishStatus() {
  StaticJsonDocument<200> doc;
  doc["status"] = cafeteiraLigada ? "ligada" : "desligada";
  doc["temperature"] = String(temperatura, 1);
  doc["water_level"] = String(nivelAgua);

  char buffer[200];
  serializeJson(doc, buffer);
  client.publish(mqtt_topic_status, buffer);
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("Mensagem recebida [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);

  if (message == "ligar") {
    digitalWrite(RELE_CAFETEIRA, HIGH);
    cafeteiraLigada = true;
  }
  else if (message == "desligar") {
    digitalWrite(RELE_CAFETEIRA, LOW);
    cafeteiraLigada = false;
  }

  publishStatus();
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

void lerSensores() {
  // Ler temperatura (exemplo com LM35)
  int rawTemp = analogRead(SENSOR_TEMP);
  temperatura = (rawTemp * 3.3 / 1024.0) * 100.0;

  // Ler nível de água
  nivelAgua = digitalRead(SENSOR_NIVEL) ? 100 : 0;
}

void setup() {
  pinMode(RELE_CAFETEIRA, OUTPUT);
  pinMode(SENSOR_NIVEL, INPUT);
  digitalWrite(RELE_CAFETEIRA, LOW);
  
  Serial.begin(115200);
  setup_wifi();
  
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Atualizar leituras e status a cada 5 segundos
  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate > 5000) {
    lerSensores();
    publishStatus();
    lastUpdate = millis();
  }
}