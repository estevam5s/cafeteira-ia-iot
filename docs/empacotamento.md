# Sistema CoffeeAI - Documentação Técnica

## 1. Visão Geral
O CoffeeAI é um sistema de automação para cafeteiras que integra IoT e inteligência artificial para controle e monitoramento.

### 1.1 Características Principais
- Controle remoto via interface web
- Monitoramento em tempo real
- Integração com Arduino
- Sistema de chat inteligente
- Gestão de usuários
- Monitoramento de temperatura e pressão

## 2. Requisitos do Sistema

### 2.1 Hardware
- Arduino (com chip CH340 ou similar)
- Sensores de temperatura
- Sensores de pressão
- Computador com porta USB disponível

### 2.2 Software
- Python 3.8 ou superior
- Navegador web moderno
- Driver CH340 (para Arduino)

### 2.3 Dependências Python
```
flask
flask-cors
paho-mqtt
pyserial
requests
jwt
sqlite3
```

## 3. Instalação

### 3.1 Preparação do Ambiente
1. Clone o repositório:
```bash
git clone [url-do-repositorio]
cd cafeteira-ia-iot
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

### 3.2 Configuração do Arduino
1. Instale o driver CH340 apropriado para seu sistema operacional
2. Conecte o Arduino via USB
3. Verifique a porta COM (Windows) ou /dev/ttyUSB* (Linux)

### 3.3 Compilação do Executável
1. Instale o PyInstaller:
```bash
pip install pyinstaller
```

2. Execute o script de configuração:
```bash
python setup_pyinstaller.py
```

3. Compile o executável:
```bash
python -m PyInstaller coffee.spec
```

## 4. Estrutura do Projeto
```
cafeteira-ia-iot/
├── app.py              # Aplicação principal
├── templates/          # Templates HTML
├── static/            # Arquivos estáticos
├── coffee.db          # Banco de dados SQLite
├── setup_pyinstaller.py # Script de configuração
├── requirements.txt    # Dependências
└── docs/              # Documentação
```

## 5. Uso do Sistema

### 5.1 Iniciando o Sistema
1. Conecte o Arduino ao computador
2. Execute o arquivo `run_coffee.bat`
3. Acesse `http://localhost:5000` no navegador

### 5.2 Login Inicial
- Email: admin@example.com
- Senha: admin123

### 5.3 Funcionalidades Principais
- **Dashboard**: Monitoramento em tempo real
- **Controle**: Ligar/desligar cafeteira
- **Chat**: Assistente virtual para comandos
- **Configurações**: Ajustes do sistema

## 6. Comandos do Chat
- "ligar cafeteira" - Liga o sistema
- "desligar cafeteira" - Desliga o sistema
- "status" - Verifica estado atual
- "verificar arduino" - Testa conexão com Arduino

## 7. Manutenção

### 7.1 Banco de Dados
- Localização: `coffee.db`
- Tipo: SQLite
- Tabelas principais:
  - users: Gestão de usuários
  - logs: Registro de atividades

### 7.2 Logs
- Verificar `app.log` para diagnóstico
- Logs do Arduino via porta serial

### 7.3 Backup
Recomenda-se backup regular de:
- Banco de dados (coffee.db)
- Configurações personalizadas
- Logs do sistema

## 8. Resolução de Problemas

### 8.1 Arduino não Conecta
1. Verifique se o driver CH340 está instalado
2. Confirme a porta COM correta
3. Reinicie o sistema se necessário

### 8.2 Erros Comuns
- **Erro 404**: Verifique se o servidor está rodando
- **Erro de Conexão**: Verifique Arduino e cabos
- **Erro de Autenticação**: Verifique credenciais

## 9. Segurança

### 9.1 Autenticação
- Sistema baseado em JWT
- Tokens com validade de 24 horas
- Senhas armazenadas com hash

### 9.2 Comunicação
- HTTPS recomendado para produção
- MQTT com TLS quando possível

## 10. Contato e Suporte
- Suporte Técnico: [email]
- Documentação Online: [url]
- Repositório: [github-url]

## 11. Atualizações e Versionamento
- Versão atual: 1.0.0
- Verificar atualizações: [url-updates]
- Changelog disponível no repositório

## 12. Licença
[Tipo de Licença] - Veja LICENSE.md para detalhes