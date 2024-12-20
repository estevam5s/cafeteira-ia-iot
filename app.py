from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
CORS(app)

# Configurações Dify
DIFY_API_KEY = 'app-TgulottYoZSmZkVGtfTjR9EK'

DIFY_API_URL = 'https://api.dify.ai/v1'

# Configurações MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = "cafeteira/comando"
MQTT_TOPIC_STATUS = "cafeteira/status"

# Estado global da cafeteira
coffee_state = {
    "status": "desligada",
    "last_activity": "",
    "temperature": "0"
}

# Configuração do cliente MQTT
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Conectado ao broker MQTT com código: {rc}")
    client.subscribe([(MQTT_TOPIC_COMMAND, 0), (MQTT_TOPIC_STATUS, 0)])

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"Mensagem recebida no tópico {msg.topic}: {payload}")
        
        if msg.topic == MQTT_TOPIC_STATUS:
            update_coffee_state(payload)
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {e}")

def update_coffee_state(payload):
    global coffee_state
    try:
        data = json.loads(payload)
        coffee_state.update(data)
    except:
        if payload in ["ligada", "desligada"]:
            coffee_state["status"] = payload
    coffee_state["last_activity"] = datetime.now().strftime("%H:%M:%S")

def process_command(message):
    """Processa o comando e retorna a ação correta"""
    message = message.lower().strip()
    
    # Log para debug
    print(f"Processando comando: '{message}'")
    
    if "ligar" in message and "cafeteira" in message:
        print("Comando identificado: LIGAR")
        return "ligar"
    elif "desligar" in message and "cafeteira" in message:
        print("Comando identificado: DESLIGAR")
        return "desligar"
    else:
        print("Nenhum comando identificado")
        return None

def connect_mqtt():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("Conectado ao broker MQTT")
    except Exception as e:
        print(f"Erro ao conectar ao MQTT: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').lower()
        
        # Log detalhado
        print("\n=== Nova Mensagem ===")
        print(f"Mensagem recebida: '{message}'")
        
        # Headers para a API do Dify
        headers = {
            'Authorization': f'Bearer {DIFY_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Enviar mensagem para o Dify
        dify_response = requests.post(
            f'{DIFY_API_URL}/chat-messages',
            headers=headers,
            json={
                'conversation_id': data.get('conversation_id'),
                'inputs': {},
                'query': message,
                'response_mode': "blocking",
                'user': "user"
            }
        )
        
        response_data = dify_response.json()
        
        # Processar comando com mais logs
        if 'ligar' in message and 'cafeteira' in message:
            print("Comando detectado: LIGAR")
            mqtt_client.publish(MQTT_TOPIC_COMMAND, "ligar")
        elif 'desligar' in message and 'cafeteira' in message:
            print("Comando detectado: DESLIGAR")
            mqtt_client.publish(MQTT_TOPIC_COMMAND, "desligar")
        
        print("=== Fim do Processamento ===\n")
        return jsonify(response_data)

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(coffee_state)

if __name__ == '__main__':
    connect_mqtt()
    app.run(debug=True)