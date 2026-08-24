from __future__ import annotations

import json
import secrets
import smtplib
import string
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
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


class ServerLinkCodeRequest(BaseModel):
    minecraft_nick: str = Field(min_length=3, max_length=32)
    minecraft_uuid: str | None = Field(default=None, max_length=36)


class ServerInventoryRequest(BaseModel):
    minecraft_nick: str = Field(min_length=3, max_length=32)
    minecraft_uuid: str | None = Field(default=None, max_length=36)
    inventory: list[dict[str, Any]] = Field(default_factory=list)
    equipment: dict[str, Any] | None = None
    ender_chest: list[dict[str, Any]] | None = None


class PasswordResetRequest(BaseModel):
    minecraft_nick: str = Field(min_length=3, max_length=32)
    email: str = Field(min_length=5, max_length=255)


class PasswordResetConfirmRequest(BaseModel):
    minecraft_nick: str = Field(min_length=3, max_length=32)
    code: str = Field(min_length=6, max_length=16)
    new_password: str = Field(min_length=6, max_length=128)


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


def ensure_runtime_schema(settings: Settings) -> None:
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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS player_inventory_snapshots (
                  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                  minecraft_nick VARCHAR(32) NOT NULL,
                  minecraft_uuid CHAR(36) NULL,
                  inventory_json JSON NOT NULL,
                  equipment_json JSON NULL,
                  ender_chest_json JSON NULL,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  UNIQUE KEY uq_inventory_nick (minecraft_nick),
                  KEY idx_inventory_uuid (minecraft_uuid),
                  KEY idx_inventory_updated_at (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS password_reset_codes (
                  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                  user_id BIGINT UNSIGNED NOT NULL,
                  code_hash CHAR(64) NOT NULL,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  expires_at TIMESTAMP NOT NULL,
                  used_at TIMESTAMP NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY uq_password_reset_code_hash (code_hash),
                  KEY idx_password_reset_user (user_id),
                  KEY idx_password_reset_expires (expires_at),
                  CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )


def require_server_secret(settings: Settings, secret_header: str) -> None:
    if not secret_header or not secrets.compare_digest(secret_header, settings.server_secret):
        raise HTTPException(status_code=403, detail="Серверный доступ запрещён.")


def make_short_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def decode_json_field(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


def send_password_reset_email(settings: Settings, email: str, nick: str, code: str) -> bool:
    if not settings.smtp_host or not settings.smtp_from:
        return False
    message = EmailMessage()
    message["Subject"] = "HORDE Minecraft: код восстановления пароля"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Привет, {nick}!",
                "",
                "Код восстановления пароля HORDE:",
                code,
                "",
                "Код действует 20 минут. Если это были не вы, просто игнорируйте письмо.",
            ]
        )
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_tls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True
    except Exception:
        return False


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
    schema_ready = False
    app = FastAPI(title="HORDE Auth API", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def ensure_schema_ready() -> None:
        nonlocal schema_ready
        if schema_ready:
            return
        ensure_runtime_schema(settings)
        schema_ready = True

    @app.on_event("startup")
    def startup() -> None:
        print("HORDE auth: API started; database schema will be checked lazily.", flush=True)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/db-health")
    def db_health() -> dict[str, str]:
        ensure_schema_ready()
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                row = cur.fetchone()
        return {"status": "ok" if row and row["ok"] == 1 else "db_error"}

    @app.post("/auth/register")
    def register(payload: RegisterRequest, request: Request) -> dict[str, Any]:
        ensure_schema_ready()
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
        ensure_schema_ready()
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
        ensure_schema_ready()
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
        ensure_schema_ready()
        user = get_user_by_session(settings, authorization)
        return {"user": public_user(user)}

    @app.get("/auth/inventory")
    def my_inventory(authorization: str = Header(default="")) -> dict[str, Any]:
        ensure_schema_ready()
        user = get_user_by_session(settings, authorization)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT inventory_json, equipment_json, ender_chest_json, updated_at
                    FROM player_inventory_snapshots
                    WHERE minecraft_nick=%s
                    """,
                    (user["minecraft_nick"],),
                )
                row = cur.fetchone()
        if not row:
            return {
                "synced": False,
                "minecraft_nick": user["minecraft_nick"],
                "inventory": [],
                "equipment": {},
                "ender_chest": [],
            }
        return {
            "synced": True,
            "minecraft_nick": user["minecraft_nick"],
            "inventory": decode_json_field(row.get("inventory_json"), []),
            "equipment": decode_json_field(row.get("equipment_json"), {}),
            "ender_chest": decode_json_field(row.get("ender_chest_json"), []),
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        }

    @app.post("/auth/skin")
    def update_skin(payload: SkinUpdateRequest, authorization: str = Header(default="")) -> dict[str, Any]:
        ensure_schema_ready()
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

    @app.post("/auth/password-reset/request")
    def password_reset_request(payload: PasswordResetRequest) -> dict[str, Any]:
        ensure_schema_ready()
        nick = normalize_nick(payload.minecraft_nick)
        email = payload.email.strip().lower()
        now = utcnow().replace(tzinfo=None)
        code = make_short_code(8)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE minecraft_nick=%s AND LOWER(email)=LOWER(%s)", (nick, email))
                user = cur.fetchone()
                if user:
                    cur.execute(
                        """
                        INSERT INTO password_reset_codes (user_id, code_hash, expires_at)
                        VALUES (%s, %s, %s)
                        """,
                        (user["id"], token_hash(code, settings.server_secret), now + timedelta(minutes=20)),
                    )
                    send_password_reset_email(settings, email, nick, code)
        return {"ok": True, "message": "Если почта совпала с аккаунтом, код восстановления будет отправлен."}

    @app.post("/auth/password-reset/confirm")
    def password_reset_confirm(payload: PasswordResetConfirmRequest, request: Request) -> dict[str, Any]:
        ensure_schema_ready()
        nick = normalize_nick(payload.minecraft_nick)
        code_digest = token_hash(payload.code.strip().upper(), settings.server_secret)
        now = utcnow().replace(tzinfo=None)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pr.*, u.minecraft_nick FROM password_reset_codes pr
                    JOIN users u ON u.id=pr.user_id
                    WHERE u.minecraft_nick=%s AND pr.code_hash=%s AND pr.used_at IS NULL AND pr.expires_at > %s
                    ORDER BY pr.id DESC LIMIT 1
                    """,
                    (nick, code_digest, now),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="Код восстановления неверный или истёк.")
                cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hash_password(payload.new_password), row["user_id"]))
                cur.execute("UPDATE password_reset_codes SET used_at=%s WHERE id=%s", (now, row["id"]))
                cur.execute("SELECT * FROM users WHERE id=%s", (row["user_id"],))
                user = cur.fetchone()
        return {"user": public_user(user), **issue_tokens(settings, user["id"], request)}

    @app.post("/server/link-code")
    def server_link_code(payload: ServerLinkCodeRequest, x_horde_server_secret: str = Header(default="")) -> dict[str, Any]:
        require_server_secret(settings, x_horde_server_secret)
        ensure_schema_ready()
        nick = normalize_nick(payload.minecraft_nick)
        code = make_short_code(8)
        now = utcnow().replace(tzinfo=None)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO site_link_codes (minecraft_nick, code_hash, expires_at)
                    VALUES (%s, %s, %s)
                    """,
                    (nick, token_hash(code, settings.server_secret), now + timedelta(minutes=10)),
                )
                if payload.minecraft_uuid:
                    cur.execute(
                        """
                        INSERT INTO users (minecraft_nick, minecraft_uuid, is_site_linked)
                        VALUES (%s, %s, 0)
                        ON DUPLICATE KEY UPDATE minecraft_uuid=COALESCE(minecraft_uuid, VALUES(minecraft_uuid))
                        """,
                        (nick, payload.minecraft_uuid),
                    )
        return {"minecraft_nick": nick, "code": code, "expires_in_seconds": 600}

    @app.post("/server/inventory")
    def server_inventory(payload: ServerInventoryRequest, x_horde_server_secret: str = Header(default="")) -> dict[str, Any]:
        require_server_secret(settings, x_horde_server_secret)
        ensure_schema_ready()
        nick = normalize_nick(payload.minecraft_nick)
        inventory_json = json.dumps(payload.inventory, ensure_ascii=False)
        equipment_json = json.dumps(payload.equipment or {}, ensure_ascii=False)
        ender_json = json.dumps(payload.ender_chest or [], ensure_ascii=False)
        with connect(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO player_inventory_snapshots
                      (minecraft_nick, minecraft_uuid, inventory_json, equipment_json, ender_chest_json)
                    VALUES (%s, %s, CAST(%s AS JSON), CAST(%s AS JSON), CAST(%s AS JSON))
                    ON DUPLICATE KEY UPDATE
                      minecraft_uuid=VALUES(minecraft_uuid),
                      inventory_json=VALUES(inventory_json),
                      equipment_json=VALUES(equipment_json),
                      ender_chest_json=VALUES(ender_chest_json),
                      updated_at=CURRENT_TIMESTAMP
                    """,
                    (nick, payload.minecraft_uuid, inventory_json, equipment_json, ender_json),
                )
        return {"ok": True, "minecraft_nick": nick}

    @app.get("/donate/subscription/{minecraft_nick}")
    def subscription(minecraft_nick: str) -> dict[str, Any]:
        ensure_schema_ready()
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
