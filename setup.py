import os
import sys
from cx_Freeze import setup, Executable

# Dependências que precisam ser incluídas
build_exe_options = {
    "packages": [
        "flask",
        "flask_cors",
        "jwt",
        "requests",
        "paho.mqtt.client",
        "serial",
        "sqlite3",
        "threading",
        "queue"
    ],
    "excludes": [],
    "include_files": [
        ("templates", "templates"),  # Inclui a pasta templates
        ("static", "static"),  # Inclui a pasta static se existir
        ("coffee.db", "coffee.db")  # Inclui o banco de dados
    ]
}

# Criação do executável
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Use this for Windows GUI applications

setup(
    name="CoffeeAI",
    version="1.0",
    description="Sistema de Controle de Cafeteira",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "app.py",  # Seu arquivo principal
            base=base,
            target_name="CoffeeAI.exe",
            icon="coffee.ico"  # Opcional: adicione um ícone se desejar
        )
    ]
)