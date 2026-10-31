FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py wsgi.py ./

# The CI pipeline passes the Git commit here, and /version reports it.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# Run as a non-root user (numeric, so Kubernetes can verify it)
RUN useradd --system --uid 10001 appuser
USER 10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

# One worker keeps Prometheus metrics correct; scale with more containers/pods.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "wsgi:app"]
