from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from functools import wraps
import requests
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import json
import jwt
import os
import sqlite3

app = Flask(__name__)
CORS(app)

# Configurações
SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta_aqui')
DATABASE = 'coffee.db'
DIFY_API_KEY = 'app-TgulottYoZSmZkVGtfTjR9EK'
DIFY_API_URL = 'https://api.dify.ai/v1'

# Configurações MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = int(os.getenv('MQTT_PORT', 1884))
MQTT_TOPIC_COMMAND = "cafeteira/comando"
MQTT_TOPIC_STATUS = "cafeteira/status"

# Variável global para último heartbeat do Arduino
last_arduino_heartbeat = None
ARDUINO_TIMEOUT = 5  # segundos para considerar Arduino desconectado

# Modifique o coffee_state
coffee_state = {
    "status": "desligada",
    "system_status": "offline",
    "last_activity": datetime.now().strftime("%H:%M:%S"),
    "temperature": "0",
    "water_level": "100",
    "maintenance_needed": False,
    "pressure": "0",
    "shots_count": 0,
    "arduino_connected": False
}

# Funções do Banco de Dados
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Configuração MQTT
mqtt_client = mqtt.Client()

# Modifique a função de conexão MQTT
def on_connect(client, userdata, flags, rc):
    print(f"Conectado ao broker MQTT com código: {rc}")
    client.subscribe([(MQTT_TOPIC_COMMAND, 0), (MQTT_TOPIC_STATUS, 0)])
    # Quando conectar, publicar uma mensagem para verificar conectividade
    client.publish("cafeteira/ping", "ping")
    global coffee_state
    coffee_state["arduino_connected"] = True

# Adicione uma função para desconexão MQTT
def on_disconnect(client, userdata, rc):
    print("Desconectado do broker MQTT")
    global coffee_state
    coffee_state["arduino_connected"] = False

def on_message(client, userdata, msg):
    global last_arduino_heartbeat
    try:
        payload = msg.payload.decode()
        print(f"Mensagem recebida no tópico {msg.topic}: {payload}")
        
        # Atualiza o heartbeat quando recebe mensagem do Arduino
        if msg.topic == "cafeteira/heartbeat":
            last_arduino_heartbeat = datetime.now()
            coffee_state["arduino_connected"] = True
        elif msg.topic == MQTT_TOPIC_STATUS:
            update_coffee_state(payload)
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {e}")


# Adicione uma função para verificar a conexão do Arduino
def is_arduino_connected():
    if last_arduino_heartbeat is None:
        return False
    time_diff = (datetime.now() - last_arduino_heartbeat).total_seconds()
    return time_diff < ARDUINO_TIMEOUT

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
                    coffee_state["system_status"] = "online" if payload == "ligada" else "offline"
        
        coffee_state["last_activity"] = datetime.now().strftime("%H:%M:%S")
        
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
        print(f"Aviso: MQTT não conectado: {e}")
        print("Continuando sem MQTT...")

# Decorator para verificar autenticação
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        
        if not token:
            return redirect(url_for('auth'))

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (data['email'],))
            current_user = cursor.fetchone()
            db.close()
            
            if current_user is None:
                return redirect(url_for('auth'))
            
            return f(dict(current_user), *args, **kwargs)
        except:
            return redirect(url_for('auth'))
            
    return decorated

# Rotas
#@app.route('/')
#def index():
#    return redirect(url_for('auth'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth():
    token = request.cookies.get('token')
    if token:
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return redirect(url_for('system'))
        except:
            pass
    return render_template('auth.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Dados incompletos'}), 400

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE email = ? AND password = ?',
            (data['email'], data['password'])
        )
        user = cursor.fetchone()
        db.close()

        if user:
            token = jwt.encode({
                'email': user['email'],
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, SECRET_KEY)
            
            response = jsonify({
                'token': token,
                'name': user['name'],
                'email': user['email']
            })
            
            # Configura o cookie
            response.set_cookie(
                'token', 
                token,
                httponly=True, 
                secure=True if not app.debug else False,
                samesite='Lax'
            )
            
            return response

        return jsonify({'message': 'Credenciais inválidas'}), 401

    except Exception as e:
        print(f"Erro no login: {e}")
        return jsonify({'message': 'Erro ao fazer login'}), 500

@app.route('/register', methods=['POST'])
def register():
    data = request.json

    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Dados incompletos'}), 400

    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (data['email'],))
        if cursor.fetchone():
            return jsonify({'message': 'Email já registrado'}), 400

        cursor.execute(
            'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
            (data['name'], data['email'], data['password'])
        )
        db.commit()
        db.close()
        return jsonify({'message': 'Usuário registrado com sucesso'}), 201

    except Exception as e:
        print(f"Erro no registro: {e}")
        return jsonify({'message': 'Erro ao registrar usuário'}), 500

@app.route('/logout')
def logout():
    response = redirect(url_for('auth'))
    response.delete_cookie('token')
    return response

@app.route('/system')
@token_required
def system(current_user):
    return render_template('system.html', user=current_user)

@app.route('/status')
def get_status():
    coffee_state["arduino_connected"] = is_arduino_connected()
    return jsonify(coffee_state)

@app.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    try:
        data = request.json
        message = data.get('message', '').lower()
        
        print(f"\nMensagem recebida: '{message}'")
        
        # Verifica se é comando para ligar e se o Arduino está conectado
        if 'ligar' in message and 'cafeteira' in message:
            if not is_arduino_connected():
                return jsonify({
                    "answer": "Não foi possível ligar a cafeteira pois o Arduino não está conectado. Por favor, verifique a conexão física do dispositivo."
                })
            
            mqtt_client.publish(MQTT_TOPIC_COMMAND, "ligar")
            coffee_state["status"] = "ligada"
            coffee_state["system_status"] = "online"
            update_coffee_state(json.dumps(coffee_state))
        
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
            coffee_state["system_status"] = "online"
            coffee_state["temperature"] = "25.0"  # Temperatura inicial
            update_coffee_state(json.dumps(coffee_state))
        elif 'desligar' in message and 'cafeteira' in message:
            mqtt_client.publish(MQTT_TOPIC_COMMAND, "desligar")
            coffee_state["status"] = "desligada"
            coffee_state["system_status"] = "offline"
            coffee_state["temperature"] = "0"  # Reseta temperatura
            update_coffee_state(json.dumps(coffee_state))
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rotas para os modais
@app.route('/guide')
def get_guide():
    return jsonify({
        "basic": {
            "commands": [
                "Ligar cafeteira - Ativa o sistema",
                "Desligar cafeteira - Desativa o sistema",
                "Status - Verifica o estado atual",
                "Temperatura - Mostra a temperatura atual",
                "Fazer café - Inicia o preparo do café",
                "Ajuda - Mostra comandos disponíveis"
            ],
            "interface": [
                "Painel de controle intuitivo",
                "Chat interativo para comandos",
                "Monitoramento em tempo real",
                "Indicadores de status visual",
                "Acesso a receitas e configurações"
            ]
        },
        "settings": {
            "temperature": {
                "espresso": "92-96°C",
                "cappuccino": "85-90°C",
                "americano": "85-87°C",
                "água quente": "85°C"
            }
        }
    })

@app.route('/recipes')
def get_recipes():
    return jsonify({
        "tradicional": {
            "espresso": {
                "name": "Espresso Tradicional",
                "temperature": "92-96°C",
                "ingredients": [
                    "18-21g café moído fino",
                    "Água filtrada",
                    "Pressão 9 bar"
                ],
                "steps": [
                    "Pré-aqueça o porta-filtro",
                    "Dose 18-21g de café",
                    "Distribua uniformemente",
                    "Tampe com 15-20kg de pressão",
                    "Extraia por 25-30 segundos"
                ],
                "tips": [
                    "Use café recém-moído",
                    "Observe a crema dourada",
                    "Mantenha temperatura estável"
                ]
            },
            "cappuccino": {
                "name": "Cappuccino Clássico",
                "temperature": "85-90°C",
                "ingredients": [
                    "1 shot de espresso",
                    "120ml de leite",
                    "Canela (opcional)"
                ],
                "steps": [
                    "Prepare o espresso",
                    "Espume o leite a 65°C",
                    "Combine em proporções iguais",
                    "Finalize com canela"
                ],
                "tips": [
                    "Use leite gelado",
                    "Espume até textura aveludada",
                    "Sirva imediatamente"
                ]
            }
        },
        "especiais": {
            "latte": {
                "name": "Café Latte",
                "temperature": "85-90°C",
                "ingredients": [
                    "1 shot de espresso",
                    "180ml de leite",
                    "Arte latte opcional"
                ],
                "steps": [
                    "Extraia o espresso",
                    "Espume o leite",
                    "Combine delicadamente",
                    "Faça arte latte"
                ],
                "tips": [
                    "Mantenha o leite cremoso",
                    "Use movimentos suaves",
                    "Pratique a arte latte"
                ]
            }
        },
        "gelados": {
            "frappuccino": {
                "name": "Frappuccino Clássico",
                "temperature": "Gelado",
                "ingredients": [
                    "1 shot de espresso",
                    "150ml de leite",
                    "Gelo",
                    "30ml de xarope",
                    "Chantilly"
                ],
                "steps": [
                    "Prepare o espresso",
                    "Adicione gelo no copo",
                    "Misture o café com leite e xarope",
                    "Bata todos os ingredientes",
                    "Finalize com chantilly"
                ],
                "tips": [
                    "Use gelo em cubos",
                    "Ajuste a doçura do xarope",
                    "Sirva imediatamente"
                ]
            },
            "cold_brew": {
                "name": "Cold Brew",
                "temperature": "Ambiente",
                "ingredients": [
                    "100g café moído grosso",
                    "1L água filtrada",
                    "Gelo"
                ],
                "steps": [
                    "Misture café e água",
                    "Deixe extrair por 12h",
                    "Filtre a mistura",
                    "Sirva com gelo"
                ],
                "tips": [
                    "Use café de torra média",
                    "Mantenha na geladeira",
                    "Dura até 2 semanas"
                ]
            }
        }
    })

@app.route('/brewing-methods')
def get_brewing_methods():
    return jsonify({
        "espresso": {
            "name": "Método Espresso",
            "equipment": [
                "Máquina de espresso",
                "Moedor de café",
                "Tamper",
                "Balança"
            ],
            "grind_size": "Fina (como sal refinado)",
            "ratio": "1:2 (café:água)",
            "time": "25-30 segundos",
            "steps": [
                "Moer 18-21g de café",
                "Distribuir uniformemente",
                "Tampar com pressão adequada",
                "Extrair observando fluxo"
            ]
        },
        "pour_over": {
            "name": "Pour Over",
            "equipment": [
                "Hario V60",
                "Filtro de papel",
                "Chaleira com gooseneck",
                "Balança"
            ],
            "grind_size": "Média-fina",
            "ratio": "1:15",
            "time": "2-3 minutos",
            "steps": [
                "Pré-molhar o filtro",
                "Adicionar café moído",
                "Fazer bloom",
                "Derramar em espiral"
            ]
        }
    })

@app.route('/equipment')
def get_equipment():
    return jsonify({
        "controllers": {
            "main": {
                "name": "Controlador Principal",
                "model": "ESP32",
                "specs": [
                    "Processador dual-core",
                    "WiFi integrado",
                    "Bluetooth 4.0",
                    "40 pinos GPIO"
                ],
                "pins": {
                    "GPIO1": "Sensor de Temperatura",
                    "GPIO2": "Sensor de Pressão",
                    "GPIO3": "Controle da Bomba",
                    "GPIO4": "LED de Status"
                }
            },
            "display": {
                "name": "Controlador de Display",
                "model": "SSD1306",
                "specs": [
                    "Display OLED 128x64",
                    "Interface I2C",
                    "Baixo consumo",
                    "Alto contraste"
                ]
            }
        },
        "sensors": {
            "temperature": {
                "name": "Sensor de Temperatura",
                "model": "DS18B20",
                "type": "Digital",
                "range": "-55°C a 125°C",
                "precision": "±0.5°C",
                "specs": [
                    "À prova d'água",
                    "Interface OneWire",
                    "Resposta rápida"
                ]
            },
            "pressure": {
                "name": "Sensor de Pressão",
                "model": "BMP280",
                "type": "Digital",
                "range": "300-1100hPa",
                "precision": "±0.12hPa",
                "specs": [
                    "Interface I2C",
                    "Alta precisão",
                    "Compensação de temperatura"
                ]
            },
            "water": {
                "name": "Sensor de Nível de Água",
                "model": "HC-SR04",
                "type": "Ultrassônico",
                "range": "2-400cm",
                "precision": "±0.3cm",
                "specs": [
                    "Não invasivo",
                    "Resposta rápida",
                    "Impermeável"
                ]
            }
        },
        "actuators": {
            "pump": {
                "name": "Bomba de Água",
                "model": "Ulka EP5",
                "specs": [
                    "48W de potência",
                    "15 bar de pressão",
                    "Vibratória",
                    "230V AC"
                ]
            },
            "heater": {
                "name": "Sistema de Aquecimento",
                "model": "Thermoblock",
                "specs": [
                    "1350W de potência",
                    "Controle PID",
                    "Aquecimento rápido",
                    "Proteção térmica"
                ]
            },
            "valve": {
                "name": "Válvula Solenoide",
                "model": "Parker 2-Way",
                "specs": [
                    "24V DC",
                    "Normalmente fechada",
                    "Resposta rápida",
                    "Alta durabilidade"
                ]
            }
        }
    })

@app.route('/maintenance-guide')
def get_maintenance():
    return jsonify({
        "daily": [
            {
                "title": "Limpeza Básica",
                "priority": "Alta",
                "tasks": [
                    "Limpar porta-filtro",
                    "Esvaziar bandeja de resíduos",
                    "Limpar vaporizador",
                    "Verificar nível de água"
                ]
            },
            {
                "title": "Verificações",
                "priority": "Média",
                "tasks": [
                    "Checar pressão",
                    "Verificar temperatura",
                    "Inspecionar vedações"
                ]
            }
        ],
        "weekly": [
            {
                "title": "Limpeza Profunda",
                "priority": "Alta",
                "tasks": [
                    "Backflush com detergente",
                    "Limpeza do grupo",
                    "Descarga do sistema",
                    "Limpeza de filtros"
                ]
            }
        ],
        "monthly": [
            {
                "title": "Manutenção Preventiva",
                "priority": "Alta",
                "tasks": [
                    "Descalcificação completa",
                    "Troca de filtros",
                    "Verificação de componentes",
                    "Calibração de sensores"
                ]
            }
        ]
    })

@app.route('/docs')
def get_docs():
    return jsonify({
        "system": {
            "title": "Sistema CoffeeAI",
            "description": "Sistema IoT para controle inteligente de cafeteira",
            "version": "1.0.0",
            "architecture": [
                "Frontend Web (React/Flask)",
                "Backend Python",
                "MQTT Broker",
                "Controlador ESP8266",
                "Sensores IoT"
            ]
        },
        "api": {
            "title": "API Documentation",
            "endpoints": [
                {
                    "path": "/status",
                    "method": "GET",
                    "description": "Retorna status atual do sistema"
                },
                {
                    "path": "/control",
                    "method": "POST",
                    "description": "Envia comandos para a cafeteira"
                }
            ]
        },
        "hardware": {
            "title": "Hardware Specs",
            "components": [
                "ESP8266 NodeMCU",
                "Sensores de Temperatura",
                "Sensores de Pressão",
                "Módulos Relé",
                "Display OLED"
            ]
        }
    })

@app.route('/features')
def get_features():
    return jsonify({
        "control": {
            "title": "Controle Inteligente",
            "features": [
                "Controle remoto via web",
                "Ajuste preciso de temperatura",
                "Programação de horários",
                "Modos personalizados"
            ]
        },
        "monitoring": {
            "title": "Monitoramento",
            "features": [
                "Status em tempo real",
                "Histórico de uso",
                "Alertas automáticos",
                "Gráficos de consumo"
            ]
        },
        "ai": {
            "title": "Inteligência Artificial",
            "features": [
                "Chatbot assistente",
                "Recomendações personalizadas",
                "Otimização automática",
                "Aprendizado de preferências"
            ]
        },
        "security": {
            "title": "Segurança",
            "features": [
                "Autenticação segura",
                "Criptografia de dados",
                "Proteção contra falhas",
                "Backup automático"
            ]
        }
    })

if __name__ == '__main__':
    init_db()
    
    # Criar usuário de teste
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', ('admin@example.com',))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                ('Admin', 'admin@example.com', 'admin123')
            )
            db.commit()
            print("Usuário de teste criado!")
        db.close()
    except Exception as e:
        print(f"Erro ao criar usuário de teste: {e}")

    # Conectar ao MQTT e iniciar o servidor
    connect_mqtt()
    app.run(debug=True)