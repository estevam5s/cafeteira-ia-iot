# Adicione seu usuário ao grupo uucp e lock
sudo usermod -a -G uucp,lock $USER

# Crie regras udev para portas seriais
sudo nano /etc/udev/rules.d/99-arduino.rules

# SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666", GROUP="uucp"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", MODE="0666", GROUP="dialout"