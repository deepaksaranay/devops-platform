"""Items API: the workload deployed by the DevOps platform."""
import json
import logging
import os
import sys
import time

from flask import Flask, Response, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

APP_VERSION = os.environ.get("APP_VERSION", "dev")

REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["endpoint"]
)

# One JSON object per line, so a log system (Loki) can parse the fields.
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


class MemoryStore:
    """Keeps items in memory. Used for local runs and tests."""

    def __init__(self):
        self._items = []

    def list_items(self):
        return list(self._items)

    def add_item(self, name):
        item = {"id": len(self._items) + 1, "name": name}
        self._items.append(item)
        return item

    def ping(self):
        return True


class PostgresStore:
    """Keeps items in PostgreSQL. Used when DATABASE_URL is set."""

    def __init__(self, url):
        import psycopg2

        self._psycopg2 = psycopg2
        self._url = url
        self._run(
            "CREATE TABLE IF NOT EXISTS items "
            "(id SERIAL PRIMARY KEY, name TEXT NOT NULL)"
        )

    def _run(self, sql, params=(), fetch=False):
        conn = self._psycopg2.connect(self._url)
        try:
            with conn, conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall() if fetch else None
        finally:
            conn.close()

    def list_items(self):
        rows = self._run("SELECT id, name FROM items ORDER BY id", fetch=True)
        return [{"id": row[0], "name": row[1]} for row in rows]

    def add_item(self, name):
        rows = self._run(
            "INSERT INTO items (name) VALUES (%s) RETURNING id", (name,), fetch=True
        )
        return {"id": rows[0][0], "name": name}

    def ping(self):
        self._run("SELECT 1")
        return True


def build_store(retries=30, delay=2):
    """Pick the store from the environment. Retry while the database starts up."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return MemoryStore()
    for attempt in range(1, retries + 1):
        try:
            return PostgresStore(url)
        except Exception as exc:  # database not ready yet
            logger.info(json.dumps({
                "event": "database_not_ready", "attempt": attempt, "error": str(exc),
            }))
            time.sleep(delay)
    raise RuntimeError("could not connect to the database")


def create_app(store, debug_endpoints=False):
    app = Flask(__name__)

    @app.before_request
    def start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def record_request(response):
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        elapsed = time.perf_counter() - g.get("start", time.perf_counter())
        REQUESTS.labels(request.method, endpoint, response.status_code).inc()
        LATENCY.labels(endpoint).observe(elapsed)
        if endpoint not in ("/metrics", "/health", "/ready"):
            logger.info(json.dumps({
                "event": "request",
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
            }))
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/ready")
    def ready():
        try:
            store.ping()
        except Exception:
            return jsonify(status="database unavailable"), 503
        return jsonify(status="ready")

    @app.get("/version")
    def version():
        return jsonify(version=APP_VERSION)

    @app.get("/items")
    def list_items():
        return jsonify(store.list_items())

    @app.post("/items")
    def add_item():
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify(error="name is required"), 400
        return jsonify(store.add_item(name)), 201

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    if debug_endpoints:
        # Lets you trigger the 5xx alert on purpose. Never enable this in production.
        @app.get("/debug/error")
        def debug_error():
            raise RuntimeError("deliberate error for alert testing")

    return app
