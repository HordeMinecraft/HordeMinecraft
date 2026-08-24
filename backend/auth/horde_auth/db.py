from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.connections import Connection

from .config import Settings


@contextmanager
def connect(settings: Settings) -> Iterator[Connection]:
    ssl = {"ca": settings.db_ssl_ca} if settings.db_ssl_ca else None
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        ssl=ssl,
        connect_timeout=4,
        read_timeout=6,
        write_timeout=6,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

