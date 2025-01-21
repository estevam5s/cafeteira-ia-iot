import os
from pathlib import Path

# Cria o arquivo .spec para o PyInstaller
spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('coffee.db', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_cors',
        'jwt',
        'requests',
        'paho.mqtt.client',
        'serial',
        'sqlite3',
        'threading',
        'queue'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CoffeeAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

# Escreve o arquivo .spec
with open('coffee.spec', 'w') as f:
    f.write(spec_content)

print("Arquivo spec criado. Agora execute os seguintes comandos:")
print("\n1. Instale o PyInstaller:")
print("pip install pyinstaller")
print("\n2. Execute o PyInstaller:")
print("pyinstaller coffee.spec")