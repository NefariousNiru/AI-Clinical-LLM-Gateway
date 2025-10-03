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

# copy code
COPY gateway ./gateway
COPY proto ./proto
COPY server.py ./
COPY README.md LICENSE.md ./

EXPOSE 50051
CMD ["python", "server.py"]
