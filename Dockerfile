FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias si las hubiera
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copiar archivos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY v2x_service.py .

# Exponer el puerto del dashboard Flask
EXPOSE 5000

# Comando para ejecutar el servicio
CMD ["python", "v2x_service.py"]