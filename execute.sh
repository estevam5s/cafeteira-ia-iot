# Limpe compilações anteriores
rm -rf build dist
rm -f *.spec

# Instale novamente o PyInstaller
pip install --upgrade pyinstaller

# Crie o spec e compile
python setup_pyinstaller.py
python -m PyInstaller coffee.spec