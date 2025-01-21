# Configuração do Ambiente no Arch Linux para o Sistema de Controle da Cafeteira

## 1. Requisitos do Sistema

### 1.1 Pacotes Base
```bash
sudo pacman -S python python-pip git base-devel
```

### 1.2 Dependências para Comunicação Serial
```bash
sudo pacman -S python-pyserial
```

### 1.3 Pacotes para MQTT
```bash
sudo pacman -S mosquitto
```

## 2. Configuração do Ambiente Python

### 2.1 Criação do Ambiente Virtual
```bash
python -m venv venv
source venv/bin/activate
```

### 2.2 Instalação das Dependências
```bash
pip install -r requirements.txt
```

## 3. Configuração das Permissões USB

### 3.1 Criar Regra udev
```bash
sudo nano /etc/udev/rules.d/99-arduino.rules
```

Adicione as seguintes regras:
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", MODE="0666", GROUP="dialout"
```

### 3.2 Adicionar Usuário ao Grupo
```bash
sudo usermod -a -G dialout $USER
sudo usermod -a -G uucp $USER
```

### 3.3 Recarregar Regras
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## 4. Configuração do MQTT

### 4.1 Iniciar e Habilitar Mosquitto
```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 4.2 Configurar Mosquitto
```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

Adicione:
```
listener 1884
allow_anonymous true
```

### 4.3 Reiniciar Mosquitto
```bash
sudo systemctl restart mosquitto
```

## 5. Configuração do Arduino

### 5.1 Instalar Arduino IDE
```bash
sudo pacman -S arduino
```

### 5.2 Instalar Bibliotecas
No Arduino IDE, instale:
- PubSubClient
- ArduinoJson
- OneWire
- DallasTemperature

## 6. Testes e Verificação

### 6.1 Verificar Portas Seriais
```bash
ls -l /dev/ttyUSB*
ls -l /dev/ttyACM*
ls -l /dev/ttyS*
```

### 6.2 Testar Comunicação Serial
```bash
# Monitor serial
sudo minicom -D /dev/ttyS4 -b 115200
```

### 6.3 Testar MQTT
```bash
# Subscrever tópico
mosquitto_sub -t "cafeteira/#" -p 1884

# Publicar mensagem
mosquitto_pub -t "cafeteira/comando" -m "ping" -p 1884
```

## 7. Solução de Problemas

### 7.1 Problemas de Permissão
Se ocorrerem problemas de permissão:
```bash
sudo chmod 666 /dev/ttyS4
sudo chmod 666 /dev/ttyUSB0
```

### 7.2 Liberar Porta em Uso
```bash
sudo fuser -k /dev/ttyS4
sudo fuser -k /dev/ttyUSB0
```

### 7.3 Verificar Logs
```bash
# Logs do sistema
journalctl -f

# Logs do Mosquitto
journalctl -u mosquitto -f

# Logs da aplicação
tail -f coffee_control.log
```

## 8. Executando a Aplicação

### 8.1 Iniciar o Servidor
```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar aplicação
python app.py
```

### 8.2 Verificar Status
```bash
# Verificar processos
ps aux | grep python
ps aux | grep mosquitto

# Verificar portas em uso
sudo netstat -tulpn | grep -E "1884|5000"
```

## 9. Manutenção

### 9.1 Backup do Banco de Dados
```bash
# Backup
cp coffee.db coffee.db.backup

# Restaurar
cp coffee.db.backup coffee.db
```

### 9.2 Limpeza de Logs
```bash
# Limpar logs antigos
find . -name "*.log" -mtime +7 -delete
```

### 9.3 Atualização do Sistema
```bash
# Atualizar pacotes
sudo pacman -Syu

# Atualizar dependências Python
pip install --upgrade -r requirements.txt
```