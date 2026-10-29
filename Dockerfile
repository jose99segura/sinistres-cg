# The image re-creates the database at build time from the insurers' public PDFs (checked against the
# sha256 in contracts.yaml) and the committed segmentation in data/segments/: no model call, no key.
FROM python:3.12-slim AS app

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY contracts.yaml ./
COPY data/segments/*.json data/segments/
# Local copies when present (deploys from a workstation); otherwise the build downloads them.
COPY data/pdfs/ data/pdfs/
COPY sinistres sinistres
COPY eval/cases.yaml eval/report.json* eval/comparison.json* eval/
RUN uv sync --frozen --no-dev \
 && uv run --no-sync sinistres build \
 && useradd --create-home --uid 10001 app \
 && chown -R app /app/data

USER app
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn sinistres.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
