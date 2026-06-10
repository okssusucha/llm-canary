FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir ".[server]"

VOLUME /data
EXPOSE 8080

CMD ["llm-canary", "serve", "--host", "0.0.0.0", "--port", "8080", "--db", "/data/canary.db"]
