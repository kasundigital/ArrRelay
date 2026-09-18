from __future__ import annotations

import asyncio
import logging
import os
import secrets

import uvicorn

from .config import get_settings
from .database import Database
from .runtime import RuntimeManager
from .web import create_app


def ensure_app_secret(base):
    """Create a persistent application secret automatically on first run."""
    if base.app_secret and base.app_secret != "change-me-in-production":
        return base

    secret_path = os.path.join(os.path.dirname(base.database_path) or "/data", ".arrrelay_secret")
    os.makedirs(os.path.dirname(secret_path), exist_ok=True)

    if os.path.exists(secret_path):
        secret = open(secret_path, "r", encoding="utf-8").read().strip()
    else:
        secret = secrets.token_hex(32)
        with open(secret_path, "w", encoding="utf-8") as handle:
            handle.write(secret)
        try:
            os.chmod(secret_path, 0o600)
        except OSError:
            pass

    return base.model_copy(update={"app_secret": secret})


async def main():
    base = ensure_app_secret(get_settings())

    logging.basicConfig(
        level=getattr(logging, base.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    db = Database(base.database_path)
    await db.init()

    runtime = RuntimeManager(base, db)
    await runtime.start()

    app = create_app(base, db, runtime)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=base.web_host,
            port=base.web_port,
            log_level=base.log_level.lower(),
        )
    )

    try:
        await server.serve()
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
