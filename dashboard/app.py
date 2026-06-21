#!/usr/bin/env python3
"""
dashboard/app.py
Backend Flask que expone los datos del honeypot como API REST y sirve
el panel de visualización en tiempo real.

Uso:
    python dashboard/app.py
    -> abre http://localhost:5000
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, render_template

from honeypot import logger

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(logger.get_stats())


@app.route("/api/attempts")
def api_attempts():
    return jsonify(logger.get_recent_attempts(limit=100))


if __name__ == "__main__":
    logger.init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
