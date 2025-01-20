from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from functools import wraps
import requests
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import json
import jwt
import os
import time
import sqlite3
import serial
import serial.tools.list_ports
import glob
import subprocess
import threading
import queue

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

# Configuração da comunicação serial
arduino_serial = None
BAUD_RATE = 115200  # Mesma taxa do Arduino

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

# Variável global para controle da conexão do Arduino
arduino_connection = {
    "is_connected": False,
    "last_heartbeat": None,
    "timeout": 10  # segundos para considerar desconectado
}

def find_arduino_port():
    """
    Encontra a porta do Arduino no Linux de forma mais robusta
    """
    # Procura por dispositivos USB Serial no Linux
    if os.path.exists('/dev/serial/by-id'):
        try:
            # Lista todos os dispositivos USB serial
            devices = glob.glob('/dev/serial/by-id/*')
            for device in devices:
                if 'ch340' in device.lower() or 'acm' in device.lower() or 'usb' in device.lower():
                    # Obtém o caminho real do dispositivo
                    real_path = os.path.realpath(device)
                    print(f"Dispositivo encontrado: {device} -> {real_path}")
                    return real_path
        except Exception as e:
            print(f"Erro ao procurar dispositivo: {e}")
    
    # Fallback: procura portas USB diretamente
    try:
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        if ports:
            print(f"Porta encontrada: {ports[0]}")
            return ports[0]
    except Exception as e:
        print(f"Erro ao listar portas: {e}")
    
    return None

def serial_listener(serial_port, message_queue):
    while True:
        try:
            if serial_port and serial_port.is_open and serial_port.in_waiting:
                msg = serial_port.readline().decode().strip()
                message_queue.put(msg)
                # Atualiza o timestamp do heartbeat
                global last_arduino_heartbeat
                last_arduino_heartbeat = datetime.now()
        except Exception as e:
            print(f"Erro na leitura serial: {e}")
        time.sleep(0.1)

# Função para encontrar e conectar ao Arduino
def force_release_port(port):
    """Força a liberação da porta serial."""
    try:
        os.system(f'sudo fuser -k {port}')
        time.sleep(2)  # Aguarda a liberação
        return True
    except Exception as e:
        print(f"Erro ao liberar porta: {e}")
        return False

def connect_arduino():
    """Conecta ao Arduino apenas se não estiver conectado."""
    global arduino_serial
    
    if arduino_serial and arduino_serial.is_open:
        return True  # Já conectado

    port = find_arduino_port()
    if not port:
        print("Nenhuma porta serial encontrada")
        return False

    try:
        arduino_serial = serial.Serial(port, baudrate=115200, timeout=1)
        time.sleep(2)  # Aguarda inicialização do Arduino
        print(f"Arduino conectado na porta {port}")
        return True
    except Exception as e:
        print(f"Erro ao conectar ao Arduino: {e}")
        return False

def send_command_to_arduino(command):
    """Envia comandos ao Arduino com tratamento de erros."""
    global arduino_serial
    try:
        if not connect_arduino():
            raise ConnectionError("Arduino não está conectado")

        arduino_serial.write(f"{command}\n".encode())
        arduino_serial.flush()
        print(f"Comando enviado: {command}")
        
        # Aguarda resposta do Arduino
        response = arduino_serial.readline().decode().strip()
        print(f"Resposta do Arduino: {response}")
        return response
    except Exception as e:
        print(f"Erro ao enviar comando: {e}")
        return None

def release_port(port):
    """Força a liberação da porta serial."""
    try:
        subprocess.run(['fuser', '-k', port], check=False)
        time.sleep(2)
    except Exception as e:
        print(f"Erro ao liberar porta: {e}")

def send_heartbeat():
    """Envia um ping periódico para verificar se o Arduino está ativo."""
    global arduino_serial
    try:
        if arduino_serial and arduino_serial.is_open:
            arduino_serial.write(b'ping\n')
            arduino_serial.flush()
            response = arduino_serial.readline().decode().strip()
            if response == "pong":
                print("Arduino está ativo")
                return True
    except Exception as e:
        print(f"Erro no heartbeat: {e}")
    return False

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


# Modifique a função on_message para processar o heartbeat
def on_message(client, userdata, msg):
    global arduino_connection
    try:
        payload = msg.payload.decode()
        print(f"Mensagem recebida no tópico {msg.topic}: {payload}")
        
        # Verifica se é uma mensagem de heartbeat
        if msg.topic == "cafeteira/heartbeat":
            arduino_connection["is_connected"] = True
            arduino_connection["last_heartbeat"] = datetime.now()
            coffee_state["arduino_connected"] = True
            print("Heartbeat recebido do Arduino - Conexão ativa")
            
        elif msg.topic == MQTT_TOPIC_STATUS:
            update_coffee_state(payload)
            
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {e}")

def check_arduino_connection():
    """Verifica se o Arduino está respondendo."""
    global arduino_serial
    
    if arduino_serial is None or not arduino_serial.is_open:
        return connect_arduino()

    try:
        arduino_serial.write(b'ping\n')
        arduino_serial.flush()
        time.sleep(0.1)
        
        if arduino_serial.in_waiting:
            response = arduino_serial.readline().decode().strip()
            return response == "pong"
        
        return False
    except Exception as e:
        print(f"Erro na comunicação serial: {e}")
        if arduino_serial is not None:
            try:
                arduino_serial.close()
            except:
                pass
        arduino_serial = None
        return connect_arduino()  # Tenta reconectar imediatamente

def heartbeat_check():
    global last_arduino_heartbeat
    if last_arduino_heartbeat is None or (datetime.now() - last_arduino_heartbeat).total_seconds() > ARDUINO_TIMEOUT:
        print("Arduino desconectado, tentando reconectar...")
        connect_arduino()

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
    global coffee_state
    try:
        arduino_connected = check_arduino_connection()
        coffee_state["arduino_connected"] = arduino_connected
        
        if arduino_connected:
            # Atualiza o timestamp da última atividade
            coffee_state["last_activity"] = datetime.now().strftime("%H:%M:%S")
            
        return jsonify(coffee_state)
    except Exception as e:
        print(f"Erro ao obter status: {e}")
        return jsonify({"error": "Erro ao obter status"}), 500

# @app.route('/chat', methods=['POST'])
# @token_required
# def chat(current_user):
#     try:
#         data = request.json
#         message = data.get('message', '').lower()
#         print(f"\nMensagem recebida: '{message}'")

#         # Verifica status da conexão serial do Arduino
#         arduino_connected = check_arduino_connection()

#         # Comandos relacionados ao Arduino e cafeteira
#         if 'arduino' in message and ('status' in message or 'conectado' in message):
#             if arduino_connected:
#                 return jsonify({
#                     "answer": "✅ O Arduino está conectado e comunicando via porta serial."
#                 })
#             else:
#                 return jsonify({
#                     "answer": "❌ Arduino não detectado.\n\n"
#                              "Por favor, verifique:\n"
#                              "1. Se o Arduino está conectado via USB\n"
#                              "2. Se o código correto está carregado no Arduino\n"
#                              "3. Se não há outros programas usando a porta serial"
#                 })

#         elif 'ligar' in message and 'cafeteira' in message:
#             if not arduino_connected:
#                 return jsonify({
#                     "answer": "⚠️ Não é possível ligar a cafeteira.\n\n"
#                              "O Arduino não está conectado ao sistema.\n"
#                              "Conecte o Arduino via USB e tente novamente."
#                 })

#             try:
#                 # Envia comando para o Arduino
#                 if arduino_serial:
#                     arduino_serial.write(b'ligar\n')
#                     # Aguarda confirmação do Arduino
#                     response = arduino_serial.readline().decode().strip()
#                     if response == "ok":
#                         coffee_state.update({
#                             "status": "ligada",
#                             "system_status": "online",
#                             "temperature": "25.0"
#                         })
#                         update_coffee_state(json.dumps(coffee_state))
#                     else:
#                         return jsonify({
#                             "answer": "⚠️ O Arduino não confirmou o comando. Tente novamente."
#                         })

#             except Exception as e:
#                 print(f"Erro na comunicação serial: {e}")
#                 return jsonify({
#                     "answer": "❌ Erro ao enviar comando para o Arduino."
#                 })

#         elif 'desligar' in message and 'cafeteira' in message:
#             if arduino_serial:
#                 try:
#                     arduino_serial.write(b'desligar\n')
#                     coffee_state.update({
#                         "status": "desligada",
#                         "system_status": "offline",
#                         "temperature": "0"
#                     })
#                     update_coffee_state(json.dumps(coffee_state))
#                 except Exception as e:
#                     print(f"Erro ao desligar: {e}")
#                     return jsonify({
#                         "answer": "❌ Erro ao enviar comando de desligamento."
#                     })

#         # Processamento normal do chat via Dify.ai
#         headers = {
#             'Authorization': f'Bearer {DIFY_API_KEY}',
#             'Content-Type': 'application/json'
#         }
        
#         dify_response = requests.post(
#             f'{DIFY_API_URL}/chat-messages',
#             headers=headers,
#             json={
#                 'conversation_id': data.get('conversation_id'),
#                 'inputs': {},
#                 'query': message,
#                 'response_mode': "blocking",
#                 'user': "user"
#             }
#         )
        
#         return jsonify(dify_response.json())


@app.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    try:
        data = request.json
        message = data.get('message', '').lower()
        print(f"\nMensagem recebida: '{message}'")

        # Verifica status da conexão serial do Arduino
        arduino_connected = check_arduino_connection()

        # Comandos relacionados ao Arduino e cafeteira
        if 'arduino' in message and ('status' in message or 'conectado' in message):
            if arduino_connected:
                return jsonify({
                    "answer": "✅ O Arduino está conectado e comunicando via porta serial."
                })
            else:
                return jsonify({
                    "answer": "❌ Arduino não detectado.\n\n"
                             "Por favor, verifique:\n"
                             "1. Se o Arduino está conectado via USB\n"
                             "2. Se o código correto está carregado no Arduino\n"
                             "3. Se não há outros programas usando a porta serial"
                })

        elif 'ligar' in message and 'cafeteira' in message:
            if not arduino_connected:
                return jsonify({
                    "answer": "⚠️ Não é possível ligar a cafeteira.\n\n"
                             "O Arduino não está conectado ao sistema.\n"
                             "Conecte o Arduino via USB e tente novamente."
                })

            try:
                # Envia comando para o Arduino
                if arduino_serial:
                    arduino_serial.write(b'ligar\n')
                    arduino_serial.flush()
                    time.sleep(0.5)  # Aguarda resposta do Arduino

                    if arduino_serial.in_waiting:  # Verifica se há resposta
                        response = arduino_serial.readline().decode().strip()
                        if response == "ok":
                            return jsonify({"answer": "✅ Cafeteira ligada com sucesso!"})
                        else:
                            return jsonify({"answer": f"⚠️ Resposta inesperada do Arduino: {response}"})
                    else:
                        # Tenta ligar a cafeteira novamente se não houver resposta
                        print("⚠️ Nenhuma resposta do Arduino. Tentando ligar a cafeteira novamente...")
                        arduino_serial.write(b'ligar\n')
                        arduino_serial.flush()
                        time.sleep(0.5)
                        if arduino_serial.in_waiting:
                            response = arduino_serial.readline().decode().strip()
                            if response == "ok":
                                return jsonify({"answer": "✅ Cafeteira ligada com sucesso após nova tentativa!"})
                            else:
                                return jsonify({"answer": f"⚠️ Resposta inesperada do Arduino na segunda tentativa: {response}"})
                        else:
                            return jsonify({"answer": "⚠️ Nenhuma resposta do Arduino na segunda tentativa. Tente novamente."})

            except Exception as e:
                print(f"Erro ao enviar comando: {e}")
                return jsonify({"answer": "❌ Erro ao tentar ligar a cafeteira."})

        elif 'desligar' in message and 'cafeteira' in message:
            if not arduino_connected:
                return jsonify({
                    "answer": "⚠️ Não é possível desligar a cafeteira.\n\n"
                             "O Arduino não está conectado ao sistema.\n"
                             "Conecte o Arduino via USB e tente novamente."
                })

            try:
                # Envia comando para o Arduino
                if arduino_serial:
                    arduino_serial.write(b'desligar\n')
                    arduino_serial.flush()
                    time.sleep(0.5)  # Aguarda resposta do Arduino

                    if arduino_serial.in_waiting:  # Verifica se há resposta
                        response = arduino_serial.readline().decode().strip()
                        if response == "ok":
                            return jsonify({"answer": "✅ Cafeteira desligada com sucesso!"})
                        else:
                            return jsonify({"answer": f"⚠️ Resposta inesperada do Arduino: {response}"})
                    else:
                        # Tenta desligar a cafeteira novamente se não houver resposta
                        print("⚠️ Nenhuma resposta do Arduino. Tentando desligar a cafeteira novamente...")
                        arduino_serial.write(b'desligar\n')
                        arduino_serial.flush()
                        time.sleep(0.5)
                        if arduino_serial.in_waiting:
                            response = arduino_serial.readline().decode().strip()
                            if response == "ok":
                                return jsonify({"answer": "✅ Cafeteira desligada com sucesso após nova tentativa!"})
                            else:
                                return jsonify({"answer": f"⚠️ Resposta inesperada do Arduino na segunda tentativa: {response}"})
                        else:
                            return jsonify({"answer": "⚠️ Nenhuma resposta do Arduino na segunda tentativa. Tente novamente."})

            except Exception as e:
                print(f"Erro ao enviar comando: {e}")
                return jsonify({"answer": "❌ Erro ao tentar desligar a cafeteira."})

        else:
            return jsonify({"answer": "❓ Comando não reconhecido. Por favor, tente novamente."})

    except Exception as e:
        print(f"Erro na função chat: {e}")
        return jsonify({"answer": "❌ Ocorreu um erro no processamento do comando."})

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({
            'error': str(e),
            'message': "Ocorreu um erro ao processar sua mensagem."
        }), 500

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

def main():
    init_db()
    
    try:
        # Criar usuário de teste
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

    connect_arduino()
    connect_mqtt()
    
    # Desativa reloader para evitar problemas com o terminal
    app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    main()