from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import Settings, load_settings
from .db import connect
from .security import hash_password, new_public_token, normalize_nick, token_hash, verify_password


class RegisterRequest(BaseModel):
    minecraft_nick: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    minecraft_nick: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class LinkRequest(BaseModel):
    minecraft_nick: str = Field(min_length=3, max_length=32)
    code: str = Field(min_length=4, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = Field(default=None, max_length=255)


class SkinUpdateRequest(BaseModel):
    skin_data_url: str = Field(min_length=32, max_length=700_000)
    skin_model: str = Field(default="classic", max_length=16)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "minecraft_nick": row["minecraft_nick"],
        "email": row.get("email"),
        "skin_model": row.get("skin_model") or "classic",
        "skin_data_url": row.get("skin_data_url"),
        "skin_updated_at": row["skin_updated_at"].isoformat() if row.get("skin_updated_at") else None,
    }


def ensure_skin_columns(settings: Settings) -> None:
    required = {
        "skin_model": "ALTER TABLE users ADD COLUMN skin_model ENUM('classic','slim') NOT NULL DEFAULT 'classic'",
        "skin_data_url": "ALTER TABLE users ADD COLUMN skin_data_url MEDIUMTEXT NULL",
        "skin_updated_at": "ALTER TABLE users ADD COLUMN skin_updated_at TIMESTAMP NULL",
    }
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users'
                """
            )
            existing = {row["COLUMN_NAME"] for row in cur.fetchall()}
            for column, sql in required.items():
                if column not in existing:
                    cur.execute(sql)


def get_user_by_session(settings: Settings, authorization: str) -> dict[str, Any]:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Нет токена.")
    digest = token_hash(authorization[len(prefix) :], settings.server_secret)
    now = utcnow().replace(tzinfo=None)
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.* FROM sessions s
                JOIN users u ON u.id=s.user_id
                WHERE s.session_token_hash=%s AND s.revoked_at IS NULL AND s.expires_at > %s
                """,
                (digest, now),
            )
            user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Сессия истекла.")
    return user


def issue_tokens(settings: Settings, user_id: int, request: Request) -> dict[str, str]:
    session_token = new_public_token()
    launcher_token = new_public_token()
    expires = utcnow() + timedelta(days=settings.session_days)
    ip = request.client.host if request.client else ""
    ip_hash = token_hash(ip, settings.server_secret) if ip else None

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (user_id, session_token_hash, user_agent, ip_hash, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    token_hash(session_token, settings.server_secret),
                    request.headers.get("user-agent", "")[:255],
                    ip_hash,
                    expires.replace(tzinfo=None),
                ),
            )
            cur.execute(
                """
                INSERT INTO launcher_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, token_hash(launcher_token, settings.server_secret), expires.replace(tzinfo=None)),
            )
    return {
        "session_token": session_token,
        "launcher_token": launcher_token,
        "expires_at": expires.isoformat(),
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="HORDE Auth API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.on_event("startup")
    def startup() -> None:
        ensure_skin_columns(settings)

    @app.get("/health")
    def health() -> dict[str, str]:
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                row = cur.fetchone()
        return {"status": "ok" if row and row["ok"] == 1 else "db_error"}

    @app.post("/auth/register")
    def register(payload: RegisterRequest, request: Request) -> dict[str, Any]:
        nick = normalize_nick(payload.minecraft_nick)
        pwd_hash = hash_password(payload.password)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE minecraft_nick=%s FOR UPDATE", (nick,))
                existing = cur.fetchone()
                if existing and existing.get("password_hash"):
                    raise HTTPException(status_code=409, detail="Этот ник уже зарегистрирован.")
                if existing:
                    cur.execute(
                        "UPDATE users SET password_hash=%s, email=%s WHERE id=%s",
                        (pwd_hash, payload.email, existing["id"]),
                    )
                    user_id = existing["id"]
                else:
                    cur.execute(
                        "INSERT INTO users (minecraft_nick, email, password_hash) VALUES (%s, %s, %s)",
                        (nick, payload.email, pwd_hash),
                    )
                    user_id = cur.lastrowid
                cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                user = cur.fetchone()
        return {"user": public_user(user), **issue_tokens(settings, user_id, request)}

    @app.post("/auth/login")
    def login(payload: LoginRequest, request: Request) -> dict[str, Any]:
        nick = normalize_nick(payload.minecraft_nick)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE minecraft_nick=%s", (nick,))
                user = cur.fetchone()
        if not user or not user.get("password_hash") or not verify_password(user["password_hash"], payload.password):
            raise HTTPException(status_code=401, detail="Неверный ник или пароль.")
        return {"user": public_user(user), **issue_tokens(settings, user["id"], request)}

    @app.post("/auth/link")
    def link_site_account(payload: LinkRequest, request: Request) -> dict[str, Any]:
        nick = normalize_nick(payload.minecraft_nick)
        code_digest = token_hash(payload.code.strip(), settings.server_secret)
        now = utcnow().replace(tzinfo=None)
        pwd_hash = hash_password(payload.password)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM site_link_codes
                    WHERE minecraft_nick=%s AND code_hash=%s AND used_at IS NULL AND expires_at > %s
                    ORDER BY id DESC LIMIT 1
                    """,
                    (nick, code_digest, now),
                )
                code = cur.fetchone()
                if not code:
                    raise HTTPException(status_code=400, detail="Код привязки неверный или истёк.")
                cur.execute("SELECT * FROM users WHERE minecraft_nick=%s FOR UPDATE", (nick,))
                user = cur.fetchone()
                if user:
                    cur.execute(
                        "UPDATE users SET password_hash=%s, email=COALESCE(%s, email), is_site_linked=1 WHERE id=%s",
                        (pwd_hash, payload.email, user["id"]),
                    )
                    user_id = user["id"]
                else:
                    cur.execute(
                        "INSERT INTO users (minecraft_nick, email, password_hash, is_site_linked) VALUES (%s, %s, %s, 1)",
                        (nick, payload.email, pwd_hash),
                    )
                    user_id = cur.lastrowid
                cur.execute("UPDATE site_link_codes SET used_at=%s WHERE id=%s", (now, code["id"]))
                cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                user = cur.fetchone()
        return {"user": public_user(user), **issue_tokens(settings, user_id, request)}

    @app.get("/auth/me")
    def me(authorization: str = Header(default="")) -> dict[str, Any]:
        user = get_user_by_session(settings, authorization)
        return {"user": public_user(user)}

    @app.post("/auth/skin")
    def update_skin(payload: SkinUpdateRequest, authorization: str = Header(default="")) -> dict[str, Any]:
        user = get_user_by_session(settings, authorization)
        skin_model = payload.skin_model.lower().strip()
        if skin_model not in {"classic", "slim"}:
            raise HTTPException(status_code=400, detail="Модель скина должна быть classic или slim.")
        if not payload.skin_data_url.startswith("data:image/png;base64,"):
            raise HTTPException(status_code=400, detail="Загрузите PNG-скин Minecraft.")
        now = utcnow().replace(tzinfo=None)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET skin_model=%s, skin_data_url=%s, skin_updated_at=%s WHERE id=%s",
                    (skin_model, payload.skin_data_url, now, user["id"]),
                )
                cur.execute("SELECT * FROM users WHERE id=%s", (user["id"],))
                updated = cur.fetchone()
        return {"user": public_user(updated)}

    @app.get("/donate/subscription/{minecraft_nick}")
    def subscription(minecraft_nick: str) -> dict[str, Any]:
        nick = normalize_nick(minecraft_nick)
        now = utcnow().replace(tzinfo=None)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tier, expires_at FROM donate_subscriptions
                    WHERE minecraft_nick=%s AND active=1 AND expires_at > %s
                    ORDER BY expires_at DESC LIMIT 1
                    """,
                    (nick, now),
                )
                row = cur.fetchone()
        if not row:
            return {"active": False, "minecraft_nick": nick}
        return {
            "active": True,
            "minecraft_nick": nick,
            "tier": row["tier"],
            "expires_at": row["expires_at"].isoformat(),
        }

    return app


app = create_app()
