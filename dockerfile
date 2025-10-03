# ---------- Builder: export requirements from Poetry ----------
FROM python:3.12-slim AS build
WORKDIR /srv
RUN pip install --no-cache-dir poetry==1.8.3
COPY pyproject.toml poetry.lock* ./
RUN poetry export -f requirements.txt --without-hashes -o requirements.txt

# ---------- Runtime image ----------
FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=build /srv/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# gRPC default port for your gateway
EXPOSE 50051

# If your server reads HOST/PORT from env internally, this is fine:
CMD ["python", "server.py"]

# If your server expects CLI flags instead, use:
# CMD ["sh", "-c", "python server.py --host ${HOST:-0.0.0.0} --port ${PORT:-50051} --tls ${TLS_ENABLED:-false} --log-level ${LOG_LEVEL:-INFO}"]
