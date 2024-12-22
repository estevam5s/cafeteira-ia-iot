#!/bin/bash

# Iniciar Mosquitto
service mosquitto start

# Aguardar Mosquitto iniciar
sleep 2

# Iniciar aplicação Flask
python app.py