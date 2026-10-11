FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
ENV AEGIS_GIT_BIN=git AEGIS_CVE_CACHE=/app/work/cvelistV5
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
