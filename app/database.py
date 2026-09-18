from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_message_id TEXT NOT NULL,
    discord_user_id TEXT NOT NULL,
    discord_channel_id TEXT NOT NULL,
    original_message TEXT NOT NULL,
    title TEXT,
    year INTEGER,
    media_type TEXT,
    status TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    arr_id TEXT,
    telegram_message_id TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_request_message_title
ON requests(discord_message_id, title, year, media_type);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def add_request(self, **kwargs: Any) -> int | None:
        async with aiosqlite.connect(self.path) as db:
            try:
                cursor = await db.execute(
                    """INSERT INTO requests (
                        discord_message_id, discord_user_id, discord_channel_id,
                        original_message, title, year, media_type, status, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        kwargs["discord_message_id"], kwargs["discord_user_id"], kwargs["discord_channel_id"],
                        kwargs["original_message"], kwargs.get("title"), kwargs.get("year"), kwargs.get("media_type"),
                        kwargs["status"], kwargs.get("confidence", 0),
                    ),
                )
                await db.commit()
                return int(cursor.lastrowid)
            except aiosqlite.IntegrityError:
                return None

    async def update_status(self, request_id: int, status: str, *, arr_id: str | None = None, error: str | None = None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE requests SET status = ?, arr_id = COALESCE(?, arr_id), error = ?,
                updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (status, arr_id, error, request_id),
            )
            await db.commit()

    async def stats(self) -> dict[str, int]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await (await db.execute("SELECT status, COUNT(*) c FROM requests GROUP BY status")).fetchall()
            result = {r["status"]: int(r["c"]) for r in rows}
            result["total"] = sum(result.values())
            result["movies"] = int((await (await db.execute("SELECT COUNT(*) c FROM requests WHERE media_type='movie'")).fetchone())["c"])
            result["series"] = int((await (await db.execute("SELECT COUNT(*) c FROM requests WHERE media_type='series'")).fetchone())["c"])
            return result

    async def recent_requests(self, limit: int = 25) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await (await db.execute("SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,))).fetchall()
            return [dict(r) for r in rows]

    async def get_settings(self) -> dict[str, str]:
        async with aiosqlite.connect(self.path) as db:
            rows = await (await db.execute("SELECT key, value FROM app_settings")).fetchall()
            return {k: v for k, v in rows}

    async def save_settings(self, values: dict[str, str]) -> None:
        async with aiosqlite.connect(self.path) as db:
            for key, value in values.items():
                await db.execute(
                    """INSERT INTO app_settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
                    (key, value),
                )
            await db.commit()

    async def has_admin(self) -> bool:
        async with aiosqlite.connect(self.path) as db:
            row = await (await db.execute("SELECT 1 FROM admins LIMIT 1")).fetchone()
            return row is not None

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> str:
        salt = salt or os.urandom(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return f"scrypt${salt.hex()}${digest.hex()}"

    async def create_admin(self, username: str, password: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)", (username, self._hash_password(password)))
            await db.commit()

    async def verify_admin(self, username: str, password: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            row = await (await db.execute("SELECT password_hash FROM admins WHERE username=?", (username,))).fetchone()
            if not row:
                return False
            try:
                _, salt_hex, expected_hex = row[0].split("$", 2)
                actual = self._hash_password(password, bytes.fromhex(salt_hex)).split("$", 2)[2]
                return hmac.compare_digest(actual, expected_hex)
            except Exception:
                return False
