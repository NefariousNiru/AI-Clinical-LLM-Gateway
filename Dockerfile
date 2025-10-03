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

# Install deps
COPY --from=build /srv/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what we need (don’t ship logs/__pycache__)
COPY gateway ./gateway
COPY proto ./proto
COPY README.md LICENSE.md ./

# gRPC port
EXPOSE 50051

# If your server reads HOST/PORT from env, this is fine.
# Using -m avoids path issues with packages.
ENV PYTHONPATH=/srv/gateway
CMD ["python", "gateway/server.py"]
