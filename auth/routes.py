from functools import wraps
import jwt
from datetime import datetime, timedelta
from flask import jsonify, request, render_template, redirect, url_for

# Configurações
SECRET_KEY = 'sua_chave_secreta_aqui'  # Mude em produção
users = []  # Em produção, use um banco de dados

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Verifica se o token está no header Authorization
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]
        # Verifica se o token está nos cookies
        elif request.cookies.get('token'):
            token = request.cookies.get('token')

        if not token:
            return redirect(url_for('login_page'))

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = next((user for user in users if user['email'] == data['email']), None)
            
            if current_user is None:
                return redirect(url_for('login_page'))
        except:
            return redirect(url_for('login_page'))

        return f(current_user, *args, **kwargs)
    return decorated

# Rota para página de autenticação
@app.route('/auth')
def auth_page():
    return render_template('auth.html')

# Rota para página principal (protegida)
@app.route('/')
@token_required
def index(current_user):
    return render_template('system.html', user=current_user)

# Rota de login
@app.route('/login', methods=['POST'])
def login():
    data = request.json

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Dados incompletos'}), 400

    user = next((user for user in users if user['email'] == data['email']), None)

    if user and user['password'] == data['password']:  # Em produção, use hash
        token = jwt.encode({
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, SECRET_KEY)
        
        response = jsonify({
            'token': token,
            'name': user['name'],
            'email': user['email']
        })
        
        # Define o token como cookie
        response.set_cookie('token', token, httponly=True, secure=True)
        return response

    return jsonify({'message': 'Credenciais inválidas'}), 401

# Rota de registro
@app.route('/register', methods=['POST'])
def register():
    data = request.json

    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Dados incompletos'}), 400

    if any(user['email'] == data['email'] for user in users):
        return jsonify({'message': 'Email já registrado'}), 400

    new_user = {
        'name': data['name'],
        'email': data['email'],
        'password': data['password']  # Em produção, use hash
    }
    
    users.append(new_user)
    
    return jsonify({'message': 'Usuário registrado com sucesso'}), 201

# Rota de logout
@app.route('/logout')
def logout():
    response = redirect(url_for('auth_page'))
    response.delete_cookie('token')
    return response

# Middleware para verificar autenticação em todas as rotas
@app.before_request
def check_auth():
    # Lista de rotas que não precisam de autenticação
    public_routes = ['auth_page', 'login', 'register', 'static']
    
    if request.endpoint not in public_routes:
        token = request.cookies.get('token')
        if not token:
            if request.path != '/auth':
                return redirect('/auth')