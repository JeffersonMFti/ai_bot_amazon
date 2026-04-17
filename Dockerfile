FROM python:3.12-slim

WORKDIR /app

# Instala dependências primeiro (camada cacheável)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

# Cria diretórios de runtime (não versionados)
RUN mkdir -p logs data

CMD ["python", "main.py"]
