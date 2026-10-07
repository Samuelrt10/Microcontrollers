FROM python:3.10-slim

# Instalar dependencias gráficas actualizadas de Debian
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglx-mesa0 \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir pybullet numpy

COPY digital_twin.py .

EXPOSE 4210/udp

CMD ["python", "digital_twin.py"]