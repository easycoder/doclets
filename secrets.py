from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, Response, abort


APP_DIR = Path(__file__).resolve().parent
SECRETS_DIR = Path(os.getenv("SECRETS_DIR", APP_DIR.parent)).resolve()
ALLOWED = {"token", "key"}


def read_secret(name: str) -> str:
    if name not in ALLOWED:
        abort(404)

    path = (SECRETS_DIR / name).resolve()
    if path.parent != SECRETS_DIR:
        abort(404)

    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        abort(404)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/token")
    def get_token() -> Response:
        value = read_secret("token")
        return Response(value, mimetype="text/plain", headers={"Cache-Control": "no-store"})

    @app.get("/key")
    def get_key() -> Response:
        value = read_secret("key")
        return Response(value, mimetype="text/plain", headers={"Cache-Control": "no-store"})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
