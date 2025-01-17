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

# Estado global da cafeteira
coffee_state = {
    "status": "desligada",
    "system_status": "offline",
    "last_activity": datetime.now().strftime("%H:%M:%S"),
    "temperature": "0",
    "water_level": "100",
    "maintenance_needed": False,
    "pressure": "0",
    "shots_count": 0
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
    return jsonify(coffee_state)

@app.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
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
            coffee_state["system_status"] = "online"
            update_coffee_state(json.dumps(coffee_state))
        elif 'desligar' in message and 'cafeteira' in message:
            mqtt_client.publish(MQTT_TOPIC_COMMAND, "desligar")
            coffee_state["status"] = "desligada"
            coffee_state["system_status"] = "offline"
            update_coffee_state(json.dumps(coffee_state))
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

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