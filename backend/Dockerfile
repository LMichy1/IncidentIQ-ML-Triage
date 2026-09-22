# Build with context = repo root (backend depends on the local ml/ package):
#   docker build -f backend/Dockerfile -t incidentiq-backend .
# or via docker-compose.yml at the repo root, which sets this up correctly.

# ---- Stage 1: produce the model artifact explicitly, at build time -----
# Training never happens at container startup. This stage runs the exact
# same reproducible scripts documented in ml/README.md.
FROM python:3.10-slim AS ml-builder
WORKDIR /app/ml
COPY ml/pyproject.toml ./
COPY ml/src ./src
COPY ml/scripts ./scripts
RUN pip install --no-cache-dir -e .
RUN python scripts/generate_dataset.py && python scripts/train.py

# ---- Stage 2: runtime image ---------------------------------------------
FROM python:3.10-slim AS runtime
WORKDIR /app

# incidentiq-ml first (editable, local) so backend's dependency on it
# resolves to this copy instead of hitting PyPI for a package that isn't
# published there.
COPY ml/pyproject.toml ./ml/
COPY ml/src ./ml/src
RUN pip install --no-cache-dir -e ./ml

COPY backend/pyproject.toml ./backend/
COPY backend/app ./backend/app
RUN pip install --no-cache-dir -e ./backend

# The artifact this backend loads — produced in stage 1, never generated
# here. If this COPY is missing/incomplete, ml_runtime's content-hash check
# still catches it at startup rather than silently serving garbage.
COPY --from=ml-builder /app/ml/artifacts ./ml/artifacts

ENV INCIDENTIQ_DB_PATH=/data/incidentiq.sqlite3
VOLUME ["/data"]

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
