# import os
# import sys
# from cx_Freeze import setup, Executable

# # Dependências que precisam ser incluídas
# build_exe_options = {
#     "packages": [
#         "flask",
#         "flask_cors",
#         "jwt",
#         "requests",
#         "paho.mqtt.client",
#         "serial",
#         "sqlite3",
#         "threading",
#         "queue"
#     ],
#     "excludes": [],
#     "include_files": [
#         ("templates", "templates"),  # Inclui a pasta templates
#         ("static", "static"),  # Inclui a pasta static se existir
#         ("coffee.db", "coffee.db")  # Inclui o banco de dados
#     ]
# }

# # Criação do executável
# base = None
# if sys.platform == "win32":
#     base = "Win32GUI"  # Use this for Windows GUI applications

# setup(
#     name="CoffeeAI",
#     version="1.0",
#     description="Sistema de Controle de Cafeteira",
#     options={"build_exe": build_exe_options},
#     executables=[
#         Executable(
#             "app.py",  # Seu arquivo principal
#             base=base,
#             target_name="CoffeeAI.exe",
#             icon="coffee.ico"  # Opcional: adicione um ícone se desejar
#         )
#     ]
# )

import os
import sys
from cx_Freeze import setup, Executable

# Função para coletar todos os arquivos de um diretório
def collect_files(directory):
    paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            source = os.path.join(root, file)
            target = os.path.relpath(source, directory)
            paths.append((source, os.path.join(os.path.basename(directory), target)))
    return paths

# Coleta todos os arquivos das pastas templates e static
template_files = collect_files("templates")
static_files = collect_files("static")

# Lista completa de pacotes necessários
packages = [
    "flask",
    "flask_cors",
    "jwt",
    "requests",
    "paho.mqtt.client",
    "serial",
    "sqlite3",
    "threading",
    "queue",
    "werkzeug",
    "jinja2",
    "itsdangerous",
    "click",
    "markupsafe",
    "datetime",
    "json",
    "functools",
    "os",
    "time",
    "glob",
    "subprocess",
    "pathlib",
    "logging"
]

# Configurações de build
build_exe_options = {
    "packages": packages,
    "excludes": ["tkinter", "test", "distutils"],
    "include_files": [
        *template_files,  # Inclui todos os arquivos de templates
        *static_files,    # Inclui todos os arquivos estáticos
        ("coffee.db", "coffee.db"),  # Banco de dados
    ],
    "include_msvcr": True,  # Inclui runtime do Visual C++
    "zip_include_packages": "*",
    "zip_exclude_packages": "",
    "build_exe": "build/CoffeeAI",  # Diretório de saída personalizado
}

# Configurações específicas do Windows
base = None
icon = None
if sys.platform == "win32":
    base = None  # Mantém o console para debug
    icon = "coffee.ico" if os.path.exists("coffee.ico") else None

# Executável principal
main_executable = Executable(
    script="app.py",
    base=base,
    target_name="CoffeeAI.exe",
    icon=icon,
    shortcut_name="CoffeeAI",
    shortcut_dir="DesktopFolder",
)

# Configuração do setup
setup(
    name="CoffeeAI",
    version="1.0.0",
    description="Sistema de Controle de Cafeteira Inteligente",
    author="Seu Nome",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": {
            "add_to_path": False,
            "initial_target_dir": r"[ProgramFilesFolder]\CoffeeAI",
        }
    },
    executables=[main_executable]
)

# Script para criar arquivo de inicialização
startup_script = """@echo off
cd %~dp0
echo Iniciando CoffeeAI...
start /B CoffeeAI.exe
echo Servidor iniciado! Aguarde alguns segundos...
timeout /t 5 >nul
start http://localhost:5000
echo Sistema iniciado com sucesso!
"""

# Cria o arquivo de inicialização
with open("build/CoffeeAI/start_coffee.bat", "w") as f:
    f.write(startup_script)

print("\nBuild concluído!")
print("Para executar o programa:")
print("1. Navegue até a pasta 'build/CoffeeAI'")
print("2. Execute o arquivo 'start_coffee.bat'")