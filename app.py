from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import markdown
import os

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
    "last_activity": datetime.now().strftime("%H:%M:%S"),
    "temperature": "0",
    "water_level": "100",
    "maintenance_needed": False,
    "pressure": "0",
    "shots_count": 0
}

# Catálogo de cafés
COFFEE_TYPES = {
    "espresso": {
        "name": "Espresso",
        "description": "Café concentrado e encorpado",
        "temperature": "92-96°C",
        "time": "25-30 segundos",
        "steps": [
            "Use café moído fino",
            "Dose: 18-21g de café",
            "Tampe uniformemente",
            "Extraia observando a crema"
        ],
        "tips": [
            "Pré-aqueça a xícara",
            "Monitore a temperatura",
            "Observe a crema dourada"
        ]
    },
    "cappuccino": {
        "name": "Cappuccino",
        "description": "Café com leite vaporizado e espuma",
        "temperature": "65-70°C",
        "time": "2-3 minutos",
        "steps": [
            "Prepare espresso base",
            "Vapore leite (65-70°C)",
            "Monte em camadas",
            "Finalize com canela"
        ],
        "tips": [
            "Use leite gelado",
            "Pratique a arte latte",
            "Mantenha proporções iguais"
        ]
    }
}

# Informações dos equipamentos
EQUIPMENT_INFO = {
    "controllers": {
        "arduino": {
            "name": "ESP8266",
            "specs": [
                "WiFi integrado",
                "GPIO programáveis",
                "Comunicação MQTT",
                "12 pinos digitais"
            ],
            "status": "online",
            "function": "Controle principal"
        },
        "raspberry": {
            "name": "Raspberry Pi",
            "specs": [
                "Linux/Debian",
                "Web Server",
                "Interface gráfica",
                "GPIO expandido"
            ],
            "status": "standby",
            "function": "Servidor local"
        }
    },
    "sensors": {
        "temperature": {
            "model": "DS18B20",
            "type": "Digital",
            "range": "-55°C a +125°C",
            "precision": "±0.5°C",
            "status": "active"
        },
        "water_level": {
            "model": "HC-SR04",
            "type": "Ultrassônico",
            "range": "2cm - 400cm",
            "status": "active"
        },
        "pressure": {
            "model": "BMP280",
            "type": "Digital",
            "range": "300-1100 hPa",
            "status": "active"
        }
    }
}

# Guia de manutenção
MAINTENANCE_GUIDE = {
    "daily": [
        {
            "task": "Limpeza do porta-filtro",
            "description": "Remova e lave com água quente",
            "importance": "Alta"
        },
        {
            "task": "Verificação de água",
            "description": "Certifique-se que há água suficiente",
            "importance": "Alta"
        }
    ],
    "weekly": [
        {
            "task": "Limpeza profunda",
            "description": "Use produtos específicos para cafeteira",
            "importance": "Média"
        },
        {
            "task": "Calibração",
            "description": "Verifique temperatura e pressão",
            "importance": "Média"
        }
    ],
    "monthly": [
        {
            "task": "Descalcificação",
            "description": "Use produto descalcificante apropriado",
            "importance": "Alta"
        },
        {
            "task": "Troca de filtros",
            "description": "Substitua filtros de água",
            "importance": "Alta"
        }
    ]
}

# Configuração do cliente MQTT
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Conectado ao broker MQTT com código: {rc}")
    client.subscribe([(MQTT_TOPIC_COMMAND, 0), (MQTT_TOPIC_STATUS, 0)])
    print("Inscrito nos tópicos:", MQTT_TOPIC_COMMAND, MQTT_TOPIC_STATUS)

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
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
                coffee_state.update(data)
            except json.JSONDecodeError:
                if payload in ["ligada", "desligada"]:
                    coffee_state["status"] = payload
        
        coffee_state["last_activity"] = datetime.now().strftime("%H:%M:%S")
        
        # Verificar condições de manutenção
        if float(coffee_state["temperature"]) > 95:
            coffee_state["maintenance_needed"] = True
        if int(coffee_state["water_level"]) < 20:
            coffee_state["maintenance_needed"] = True
        if coffee_state["shots_count"] > 100:
            coffee_state["maintenance_needed"] = True
            
    except Exception as e:
        print(f"Erro ao atualizar estado: {e}")
    
    print("Estado atualizado:", coffee_state)

def connect_mqtt():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("Conectado ao broker MQTT")
    except Exception as e:
        print(f"Erro ao conectar ao MQTT: {e}")

# Rotas da aplicação

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').lower()
        
        print("\n=== Nova Mensagem ===")
        print(f"Mensagem recebida: '{message}'")
        
        headers = {
            'Authorization': f'Bearer {DIFY_API_KEY}',
            'Content-Type': 'application/json'
        }
        
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
        
        # Processar comandos
        if 'ligar' in message and 'cafeteira' in message:
            mqtt_client.publish(MQTT_TOPIC_COMMAND, "ligar")
            coffee_state["status"] = "ligada"
            update_coffee_state(coffee_state)
        elif 'desligar' in message and 'cafeteira' in message:
            mqtt_client.publish(MQTT_TOPIC_COMMAND, "desligar")
            coffee_state["status"] = "desligada"
            update_coffee_state(coffee_state)
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def get_status():
    return jsonify(coffee_state)

@app.route('/coffee-types')
def get_coffee_types():
    return jsonify(COFFEE_TYPES)

@app.route('/equipment')
def get_equipment():
    return jsonify(EQUIPMENT_INFO)

@app.route('/maintenance-guide')
def get_maintenance_guide():
    return jsonify(MAINTENANCE_GUIDE)

@app.route('/system-info')
def get_system_info():
    return jsonify({
        "coffee_maker": coffee_state,
        "system": {
            "mqtt_status": "connected" if mqtt_client.is_connected() else "disconnected",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "firmware": "1.0.0",
            "sensors": {
                "temperature": EQUIPMENT_INFO["sensors"]["temperature"]["status"],
                "water_level": EQUIPMENT_INFO["sensors"]["water_level"]["status"],
                "pressure": EQUIPMENT_INFO["sensors"]["pressure"]["status"]
            }
        }
    })

@app.route('/guide')
def get_guide():
    return jsonify({
        "commands": {
            "basic": [
                "Ligar cafeteira",
                "Desligar cafeteira",
                "Status da cafeteira",
                "Temperatura atual"
            ],
            "advanced": [
                "Preparar cappuccino",
                "Ajustar temperatura",
                "Verificar pressão",
                "Iniciar limpeza"
            ]
        },
        "tips": [
            "Mantenha o equipamento limpo",
            "Use água filtrada",
            "Verifique a temperatura",
            "Calibre regularmente"
        ]
    })

if __name__ == '__main__':
    connect_mqtt()
    app.run(debug=True)