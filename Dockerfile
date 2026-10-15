FROM node:22.20.0-bookworm-slim AS frontend
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@11.0.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PORT=8000
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libxrender1 libxext6 libglib2.0-0 libexpat1 libfreetype6 libfontconfig1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.lock backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY . /app
COPY --from=frontend /build/dist /app/frontend/dist
RUN python scripts/package_source.py && useradd --create-home --uid 10001 elusim && mkdir -p /app/data && chown -R elusim:elusim /app/data
USER elusim
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/health', timeout=4)"
CMD ["sh","-c","exec uvicorn elusim.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --limit-concurrency 32 --timeout-keep-alive 5 --no-proxy-headers"]
