FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_TORCH_BACKEND=cpu
WORKDIR /app
RUN pip install --no-cache-dir "uv>=0.5,<1"
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
RUN uv pip install --python /app/.venv/bin/python --torch-backend cpu "sentence-transformers>=3.0.0"
COPY backend/kb_manage_platform ./kb_manage_platform
COPY backend/migrations ./migrations
COPY --from=frontend-build /frontend/dist ./static
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "kb_manage_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
