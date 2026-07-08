FROM python:3.11-slim

# Instalar dependencias del sistema para compilar dlib (sin paquetes gráficos)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar el código fuente
COPY app.py .

# Crear directorios para datos persistentes
RUN mkdir -p /app/data /app/imagenes_db

# Comando de inicio
CMD ["python", "app.py"]