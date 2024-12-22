FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Modifica o comando para usar o host 0.0.0.0
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]