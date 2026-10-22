# Cristocéntricos en la nube (Railway, MODO=nube): solo el panel para vigilar el avance.
# Los videos, los reels y el worker se quedan en la laptop.

# 1) Interfaz de React
FROM node:22.12.0-slim AS interfaz
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) Servidor Flask
FROM python:3.13.1-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MODO=nube
WORKDIR /app
COPY requirements-nube.txt ./
RUN pip install --no-cache-dir -r requirements-nube.txt
COPY app/ app/
COPY agentes/ agentes/
COPY servicios/ servicios/
COPY assets/ assets/
COPY servidor.py ./
COPY --from=interfaz /frontend/dist frontend/dist
RUN useradd --create-home cristo && mkdir -p datos && chown -R cristo /app/datos
USER cristo
CMD ["python", "servidor.py"]
