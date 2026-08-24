from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_ssl_ca: str | None
    server_secret: str
    cors_origins: list[str]
    session_days: int


def load_settings() -> Settings:
    load_dotenv()
    root = Path(__file__).resolve().parents[1]
    ssl_ca = os.getenv("HORDE_AUTH_DB_SSL_CA") or None
    ssl_ca_text = os.getenv("HORDE_AUTH_DB_SSL_CA_TEXT") or None
    if ssl_ca_text:
        ca_file = Path(tempfile.gettempdir()) / "horde_aiven_ca.pem"
        ca_file.write_text(ssl_ca_text.replace("\\n", "\n"), encoding="utf-8")
        ssl_ca = str(ca_file)
    elif ssl_ca and not Path(ssl_ca).is_absolute():
        ssl_ca = str(root / ssl_ca)

    return Settings(
        db_host=os.environ["HORDE_AUTH_DB_HOST"],
        db_port=int(os.getenv("HORDE_AUTH_DB_PORT", "3306")),
        db_name=os.getenv("HORDE_AUTH_DB_NAME", "defaultdb"),
        db_user=os.environ["HORDE_AUTH_DB_USER"],
        db_password=os.environ["HORDE_AUTH_DB_PASSWORD"],
        db_ssl_ca=ssl_ca,
        server_secret=os.environ["HORDE_AUTH_SERVER_SECRET"],
        cors_origins=[
            origin.strip()
            for origin in os.getenv("HORDE_AUTH_CORS_ORIGINS", "https://hordeminecraft.ru").split(",")
            if origin.strip()
        ],
        session_days=int(os.getenv("HORDE_AUTH_SESSION_DAYS", "30")),
    )
