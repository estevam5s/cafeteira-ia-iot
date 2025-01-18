# CoffeeAI Control - Sistema de Controle Inteligente de Cafeteira

## 📋 Requisitos do Sistema

### Dependências
- Docker
- Docker Compose
- Make

### Instalação das Dependências (Linux)

#### Ubuntu/Debian:
```bash
# Atualizar pacotes
sudo apt update

# Instalar Docker
sudo apt install docker.io

# Instalar Docker Compose
sudo apt install docker-compose

# Instalar Make
sudo apt install make
```

#### Arch Linux:
```bash
# Instalar Docker
sudo pacman -S docker

# Instalar Docker Compose
sudo pacman -S docker-compose

# Instalar Make
sudo pacman -S make
```

### Configuração Inicial do Docker
```bash
# Iniciar o serviço Docker
sudo systemctl start docker

# Habilitar Docker na inicialização
sudo systemctl enable docker

# Adicionar usuário ao grupo docker (evita uso de sudo)
sudo usermod -aG docker $USER

# Aplicar as mudanças de grupo
newgrp docker
```

## 🚀 Inicialização do Projeto

### 1. Estrutura de Pastas
```bash
# Criar estrutura de pastas
mkdir -p mosquitto/config mosquitto/data mosquitto/log

# Criar arquivo de configuração do Mosquitto
cat > mosquitto/config/mosquitto.conf << EOF
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
connection_messages true
EOF

# Ajustar permissões
chmod -R 755 mosquitto
```

### 2. Iniciar o Sistema
```bash
# Parar qualquer instância do Mosquitto local
sudo systemctl stop mosquitto
sudo systemctl disable mosquitto

# Limpar ambiente Docker (se necessário)
make clean

# Construir containers
make build

# Iniciar o sistema
make run
```

### 3. Verificar Status
```bash
# Ver status dos containers
make status

# Ver logs
make logs
```

## 🌐 Acessando o Sistema

1. Abra o navegador e acesse:
```
http://localhost:5000
```

2. Você verá a interface do CoffeeAI Control com:
   - Painel de controle
   - Status da cafeteira
   - Chat interativo
   - Monitoramento em tempo real

## 🛠 Comandos Disponíveis (Makefile)

```bash
# Construir o projeto
make build

# Iniciar o sistema
make run

# Parar o sistema
make stop

# Ver logs
make logs

# Ver status
make status

# Reiniciar o sistema
make restart

# Limpar ambiente
make clean
```

## 📡 Testando a Comunicação MQTT

```bash
# Inscrever-se em um tópico (em um terminal)
mosquitto_sub -h localhost -p 1884 -t "cafeteira/#" -v

# Publicar mensagem (em outro terminal)
mosquitto_pub -h localhost -p 1884 -t "cafeteira/comando" -m "ligar"
```

## 🔧 Troubleshooting

### Problemas Comuns

1. **Erro de Porta em Uso**
```bash
# Verificar processos usando a porta
sudo lsof -i :1883
sudo lsof -i :5000

# Parar processos se necessário
sudo kill <PID>
```

2. **Erro de Permissão**
```bash
# Verificar permissões do Docker
sudo chmod 666 /var/run/docker.sock

# Recarregar grupo docker
newgrp docker
```

3. **Containers Não Iniciam**
```bash
# Verificar logs detalhados
docker-compose logs -f

# Reiniciar Docker
sudo systemctl restart docker
```

## 🔄 Atualizações e Manutenção

```bash
# Atualizar e reiniciar
git pull
make clean
make build
make run

# Backup dos dados (se necessário)
cp -r mosquitto/data mosquitto/data_backup
```

## 📱 Endpoints da API

- `GET /status` - Status atual do sistema
- `POST /chat` - Enviar comandos via chat
- `GET /coffee-types` - Lista de tipos de café
- `GET /equipment-info` - Informações dos equipamentos
- `GET /maintenance-guide` - Guia de manutenção

## 🔒 Segurança

- Mantenha o arquivo `.env` seguro (não incluso no git)
- Use HTTPS em produção
- Atualize as chaves API periodicamente
- Monitore os logs regularmente

## 📊 Monitoramento

O sistema pode ser monitorado através de:
1. Interface web em localhost:5000
2. Logs do Docker (`make logs`)
3. Status dos containers (`make status`)
4. Logs do MQTT em mosquitto/log

## ⚠️ Observações Importantes

- O sistema usa a porta 5000 para a interface web
- A porta 1884 é usada para MQTT
- Certifique-se de que estas portas estejam livres
- Mantenha o Docker e Docker Compose atualizados
- Faça backup regular dos dados