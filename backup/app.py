from flask import Flask, render_template, request, jsonify, send_from_directory
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

# 1. Receitas de Café
COFFEE_RECIPES = {
    "tradicional": {
        "espresso": {
            "name": "Espresso Tradicional",
            "ingredients": ["18-21g café moído fino"],
            "steps": [
                "Pré-aqueça o porta-filtro",
                "Dose o café uniformemente",
                "Tampe com 15-20kg de pressão",
                "Extraia por 25-30 segundos"
            ],
            "tips": ["Observe a crema dourada", "Monitore a temperatura"],
            "temperature": "92-96°C",
            "pressure": "9 bar",
            "yield": "30-35ml"
        },
        "cappuccino": {
            "name": "Cappuccino Cremoso",
            "ingredients": [
                "1 shot espresso",
                "120ml leite",
                "Canela a gosto"
            ],
            "steps": [
                "Prepare o espresso base",
                "Vapore o leite (65-70°C)",
                "Monte em camadas iguais",
                "Finalize com canela"
            ],
            "tips": ["Use leite gelado", "Pratique a arte latte"],
            "temperature": "65-70°C"
        }
    },
    "especiais": {
        "latte": {
            "name": "Latte Art",
            "ingredients": [
                "1 shot espresso",
                "150ml leite"
            ],
            "steps": [
                "Prepare o espresso",
                "Vapore o leite até aveludar",
                "Despeje com técnica latte art"
            ],
            "tips": ["Movimento suave ao despejar"],
            "temperature": "65-70°C"
        },
        "mocha": {
            "name": "Mocha Especial",
            "ingredients": [
                "1 shot espresso",
                "30ml calda chocolate",
                "120ml leite",
                "Chantilly"
            ],
            "steps": [
                "Prepare o espresso",
                "Adicione chocolate",
                "Vapore o leite",
                "Finalize com chantilly"
            ],
            "temperature": "65-70°C"
        }
    },
    "gelados": {
        "frappuccino": {
            "name": "Frappuccino",
            "ingredients": [
                "1 shot espresso",
                "150ml leite",
                "Gelo",
                "30ml xarope"
            ],
            "steps": [
                "Prepare o espresso",
                "Bata com gelo e leite",
                "Adicione xarope",
                "Decore com chantilly"
            ],
            "temperature": "Gelado"
        }
    }
}

# 2. Modos de Preparo
BREWING_METHODS = {
    "espresso": {
        "name": "Método Espresso",
        "equipment": ["Máquina espresso", "Moedor", "Tamper"],
        "grind_size": "Fina",
        "ratio": "1:2 (café:água)",
        "time": "25-30 segundos",
        "temperature": "92-96°C",
        "steps": [
            "Moer o café na hora",
            "Dosar 18-21g",
            "Tampar uniformemente",
            "Extrair observando o fluxo"
        ],
        "troubleshooting": {
            "amargo": "Moagem muito fina",
            "ácido": "Moagem muito grossa",
            "fraco": "Pouco café ou moagem grossa"
        }
    },
    "manual": {
        "name": "Métodos Manuais",
        "types": {
            "hario": {
                "name": "Hario V60",
                "ratio": "1:15",
                "time": "2-3 minutos"
            },
            "chemex": {
                "name": "Chemex",
                "ratio": "1:15",
                "time": "3-4 minutos"
            }
        }
    }
}

# 3. Equipamentos e Componentes
EQUIPMENT_INFO = {
    "controllers": {
        "arduino": {
            "name": "ESP8266",
            "specs": [
                "WiFi integrado",
                "GPIO programáveis",
                "MQTT client",
                "ADC para sensores"
            ],
            "pins": {
                "D1": "Relé",
                "D2": "Temperatura",
                "D3": "Nível água"
            }
        },
        "raspberry": {
            "name": "Raspberry Pi",
            "specs": [
                "Linux/Debian",
                "Servidor web",
                "Interface gráfica",
                "GPIO expandido"
            ]
        }
    },
    "sensors": {
        "temperature": {
            "model": "DS18B20",
            "type": "Digital",
            "range": "-55°C a +125°C",
            "precision": "±0.5°C"
        },
        "water_level": {
            "model": "HC-SR04",
            "type": "Ultrassônico",
            "range": "2cm - 400cm"
        },
        "pressure": {
            "model": "BMP280",
            "type": "Digital",
            "range": "300-1100 hPa"
        }
    },
    "actuators": {
        "relay": {
            "model": "Módulo Relé 5V",
            "type": "Digital",
            "current": "10A"
        },
        "pump": {
            "model": "Bomba 15 bar",
            "pressure": "15 bar",
            "type": "Vibratory"
        }
    }
}

# 4. Guia de Manutenção
MAINTENANCE_GUIDE = {
    "daily": [
        {
            "task": "Limpeza porta-filtro",
            "description": "Remova e lave com água quente",
            "importance": "Alta",
            "frequency": "Após cada uso"
        },
        {
            "task": "Verificar água",
            "description": "Nível e qualidade da água",
            "importance": "Alta",
            "frequency": "2x ao dia"
        }
    ],
    "weekly": [
        {
            "task": "Limpeza profunda",
            "description": "Usar produto específico",
            "importance": "Média",
            "steps": [
                "Remover porta-filtro",
                "Aplicar produto",
                "Aguardar 15 min",
                "Enxaguar bem"
            ]
        }
    ],
    "monthly": [
        {
            "task": "Descalcificação",
            "description": "Processo completo",
            "importance": "Alta",
            "steps": [
                "Usar descalcificante",
                "Processo completo",
                "Enxague múltiplo"
            ]
        }
    ]
}

# 5. Documentação do Projeto
PROJECT_DOCS = {
    "overview": {
        "title": "Visão Geral",
        "description": "Sistema IoT para controle de cafeteira",
        "components": [
            "Interface web",
            "Backend Python/Flask",
            "MQTT broker",
            "Arduino/ESP8266",
            "Sensores"
        ]
    },
    "setup": {
        "requirements": {
            "hardware": [
                "ESP8266",
                "Sensores",
                "Relés"
            ],
            "software": [
                "Python 3.8+",
                "MQTT broker",
                "Arduino IDE"
            ]
        },
        "installation": [
            "Configurar MQTT",
            "Instalar dependências",
            "Configurar hardware",
            "Iniciar servidor"
        ]
    },
    "api": {
        "endpoints": [
            {
                "route": "/status",
                "method": "GET",
                "description": "Estado atual"
            },
            {
                "route": "/chat",
                "method": "POST",
                "description": "Comandos via chat"
            }
        ]
    }
}

# 6. Como Utilizar
USAGE_GUIDE = {
    "basic": {
        "commands": [
            "Ligar cafeteira",
            "Desligar cafeteira",
            "Verificar status",
            "Temperatura atual"
        ],
        "interface": [
            "Chat interativo",
            "Botões de controle",
            "Painéis de status"
        ]
    },
    "advanced": {
        "features": [
            "Controle de temperatura",
            "Monitoramento em tempo real",
            "Alertas de manutenção"
        ],
        "tips": [
            "Manter limpo",
            "Calibrar regularmente",
            "Observar indicadores"
        ]
    }
}

# Configuração MQTT
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

# Rotas da API

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').lower()
        
        print(f"\nMensagem recebida: '{message}'")
        
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

# Rotas de Status
@app.route('/status')
def get_status():
    return jsonify(coffee_state)

@app.route('/system-info')
def get_system_info():
    return jsonify({
        "coffee_maker": coffee_state,
        "system": {
            "mqtt_status": "connected" if mqtt_client.is_connected() else "disconnected",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "firmware": "1.0.0"
        }
    })

@app.route('/guide')
def get_guide():
    return jsonify({
        "basic": {
            "commands": [
                "Ligar cafeteira",
                "Desligar cafeteira",
                "Verificar temperatura",
                "Status do sistema",
                "Preparo específico (ex: 'fazer espresso')",
                "Manutenção"
            ],
            "interface": [
                "Chat interativo para comandos",
                "Botões de controle rápido",
                "Painel de status em tempo real",
                "Indicadores de temperatura",
                "Monitoramento de água"
            ]
        },
        "advanced": {
            "features": [
                "Controle de temperatura preciso",
                "Monitoramento em tempo real",
                "Alertas de manutenção",
                "Diferentes tipos de café",
                "Integração IoT"
            ],
            "tips": [
                "Mantenha o sistema sempre atualizado",
                "Faça limpeza regular",
                "Calibre os sensores mensalmente",
                "Verifique a qualidade da água",
                "Monitore a temperatura ideal"
            ]
        },
        "settings": {
            "temperature": {
                "espresso": "92-96°C",
                "cappuccino": "85-90°C",
                "water": "85°C"
            },
            "maintenance": {
                "daily": "Limpeza básica",
                "weekly": "Limpeza profunda",
                "monthly": "Descalcificação"
            }
        },
        "shortcuts": {
            "keyboard": [
                "Enter - Enviar comando",
                "Esc - Fechar modais",
                "/help - Lista de comandos",
                "/status - Estado atual"
            ],
            "voice": [
                "Ligar cafeteira",
                "Desligar cafeteira",
                "Status",
                "Temperatura"
            ]
        }
    })

# Rotas de Receitas
@app.route('/recipes')
def get_all_recipes():
    return jsonify(COFFEE_RECIPES)

@app.route('/recipes/<category>')
def get_recipes_by_category(category):
    if category in COFFEE_RECIPES:
        return jsonify(COFFEE_RECIPES[category])
    return jsonify({"error": "Categoria não encontrada"}), 404

@app.route('/recipes/<category>/<recipe>')
def get_specific_recipe(category, recipe):
    if category in COFFEE_RECIPES and recipe in COFFEE_RECIPES[category]:
        return jsonify(COFFEE_RECIPES[category][recipe])
    return jsonify({"error": "Receita não encontrada"}), 404

# Rotas de Modo de Preparo
@app.route('/brewing-methods')
def get_brewing_methods():
    return jsonify(BREWING_METHODS)

@app.route('/brewing-methods/<method>')
def get_specific_method(method):
    if method in BREWING_METHODS:
        return jsonify(BREWING_METHODS[method])
    return jsonify({"error": "Método não encontrado"}), 404

# Rotas de Equipamentos
@app.route('/equipment')
def get_equipment():
    return jsonify(EQUIPMENT_INFO)

@app.route('/maintenance-guide')
def get_maintenance_guide():
    return jsonify(MAINTENANCE_GUIDE)

@app.route('/equipment/controllers')
def get_controllers():
    return jsonify(EQUIPMENT_INFO['controllers'])

@app.route('/equipment/sensors')
def get_sensors():
    return jsonify(EQUIPMENT_INFO['sensors'])

@app.route('/equipment/actuators')
def get_actuators():
    return jsonify(EQUIPMENT_INFO['actuators'])

# Rotas de Manutenção
@app.route('/maintenance')
def get_maintenance():
    return jsonify(MAINTENANCE_GUIDE)

@app.route('/maintenance/<period>')
def get_maintenance_by_period(period):
    if period in MAINTENANCE_GUIDE:
        return jsonify(MAINTENANCE_GUIDE[period])
    return jsonify({"error": "Período não encontrado"}), 404

# Rotas de Documentação
@app.route('/docs')
def get_documentation():
    return jsonify(PROJECT_DOCS)

@app.route('/docs/<section>')
def get_docs_section(section):
    if section in PROJECT_DOCS:
        return jsonify(PROJECT_DOCS[section])
    return jsonify({"error": "Seção não encontrada"}), 404

@app.route('/docs/api/<endpoint>')
def get_api_docs(endpoint):
    if 'api' in PROJECT_DOCS:
        endpoints = {ep['route']: ep for ep in PROJECT_DOCS['api']['endpoints']}
        if f"/{endpoint}" in endpoints:
            return jsonify(endpoints[f"/{endpoint}"])
    return jsonify({"error": "Endpoint não encontrado"}), 404

# Rotas de Uso
@app.route('/usage')
def get_usage_guide():
    return jsonify(USAGE_GUIDE)

@app.route('/usage/<level>')
def get_usage_level(level):
    if level in USAGE_GUIDE:
        return jsonify(USAGE_GUIDE[level])
    return jsonify({"error": "Nível não encontrado"}), 404

# Rotas de Funcionalidades
@app.route('/features')
def get_features():
    return jsonify({
        "control": {
            "title": "Controle da Cafeteira",
            "features": [
                "Ligar/Desligar remoto",
                "Controle de temperatura",
                "Monitoramento em tempo real",
                "Status detalhado"
            ]
        },
        "automation": {
            "title": "Automação",
            "features": [
                "Agendamento de preparo",
                "Alertas de manutenção",
                "Receitas automáticas",
                "Calibração inteligente"
            ]
        },
        "monitoring": {
            "title": "Monitoramento",
            "features": [
                "Temperatura em tempo real",
                "Nível de água",
                "Pressão do sistema",
                "Contador de shots"
            ]
        },
        "ai": {
            "title": "Inteligência Artificial",
            "features": [
                "Chatbot assistente",
                "Recomendações personalizadas",
                "Análise de padrões",
                "Otimização de preparo"
            ]
        }
    })

# Rotas de Configuração
@app.route('/settings')
def get_settings():
    return jsonify({
        "machine": {
            "temperature": {
                "min": 85,
                "max": 96,
                "default": 93
            },
            "pressure": {
                "min": 8,
                "max": 10,
                "default": 9
            },
            "water_level": {
                "min": 20,
                "warning": 30,
                "max": 100
            }
        },
        "maintenance": {
            "cleaning_interval": "7 dias",
            "descaling_interval": "30 dias",
            "filter_change": "60 dias"
        },
        "notifications": {
            "temperature_alert": true,
            "maintenance_reminder": true,
            "water_level_warning": true
        }
    })

# Rota de Histórico
@app.route('/history')
def get_history():
    return jsonify({
        "daily_usage": [
            {"date": "2024-01-20", "shots": 15, "maintenance": False},
            {"date": "2024-01-21", "shots": 12, "maintenance": True}
        ],
        "maintenance_history": [
            {
                "date": "2024-01-15",
                "type": "Limpeza",
                "notes": "Descalcificação completa"
            }
        ],
        "temperature_log": [
            {"time": "10:00", "temp": 93.5},
            {"time": "10:05", "temp": 94.0}
        ]
    })

# Rotas de Suporte
@app.route('/support')
def get_support():
    return jsonify({
        "contact": {
            "email": "support@coffeeai.com",
            "phone": "+55 11 1234-5678",
            "hours": "8h às 18h"
        },
        "faq": [
            {
                "question": "Como limpar o porta-filtro?",
                "answer": "Remova e lave com água quente após cada uso"
            },
            {
                "question": "Quando descalcificar?",
                "answer": "A cada 30 dias ou 500 shots"
            }
        ],
        "troubleshooting": {
            "no_power": ["Verificar conexão", "Testar tomada"],
            "weak_coffee": ["Verificar moagem", "Ajustar dose"]
        }
    })

if __name__ == '__main__':
    connect_mqtt()
    app.run(debug=True)