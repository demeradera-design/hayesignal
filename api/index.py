"""Entrada única da Vercel (Flask). Rotas: /api/poll, /api/items, /api/signals, /api/health."""
import hmac
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request  # noqa: E402

from hayes import config  # noqa: E402
from hayes.analyzer import aggregate  # noqa: E402
from hayes.poller import poll_once  # noqa: E402
from hayes.store import Store  # noqa: E402

app = Flask(__name__)
CACHE = "public, s-maxage=15, stale-while-revalidate=30"


def _clamp(value, lo, hi, default):
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return default


@app.route("/api/poll", methods=["GET", "POST"])
def poll():
    # Fecha por padrão: sem CRON_SECRET configurado, ninguém dispara a coleta.
    if not config.CRON_SECRET:
        return jsonify(error="CRON_SECRET não configurado"), 503
    got = request.headers.get("Authorization", "").encode()
    if not hmac.compare_digest(got, f"Bearer {config.CRON_SECRET}".encode()):
        return jsonify(error="não autorizado"), 401
    return jsonify(poll_once())


@app.get("/api/items")
def items():
    limit = int(_clamp(request.args.get("limit"), 1, 200, 50))
    source = request.args.get("source")
    store = Store()
    data = store.list_items(500)
    if source:
        data = [i for i in data if i.get("source") == source]
    resp = jsonify(persistent=store.persistent, items=data[:limit])
    resp.headers["Cache-Control"] = CACHE
    return resp


@app.get("/api/signals")
def signals():
    hours = _clamp(request.args.get("hours"), 1, 168, 48.0)
    store = Store()
    resp = jsonify(
        persistent=store.persistent,
        window_hours=hours,
        signals=aggregate(store.list_items(500), hours=hours),
    )
    resp.headers["Cache-Control"] = CACHE
    return resp


@app.get("/api/health")
def health():
    store = Store()
    return jsonify(
        ok=True,
        persistent=store.persistent,
        x_api_configured=bool(config.X_BEARER_TOKEN),
        webhook_configured=bool(config.WEBHOOK_URL),
        feeds=[n for n, _ in config.feeds()],
        last_poll=store.get("hayes:last_poll"),
    )
