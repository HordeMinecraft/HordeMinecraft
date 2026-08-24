from __future__ import annotations

import argparse
import getpass
import os
from datetime import datetime, timezone
from pathlib import Path

import pymysql

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path: Path | None = None) -> bool:
        return False


def parse_java_properties(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="ISO-8859-1").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        data[key.strip()] = value.strip()
    return data


def subscriptions_from_properties(props: dict[str, str]) -> list[tuple[str, str, int]]:
    result: list[tuple[str, str, int]] = []
    nicks = sorted({key[:-5] for key in props if key.endswith(".tier")})
    for nick in nicks:
        tier = props.get(f"{nick}.tier")
        expires = props.get(f"{nick}.expires")
        if not tier or not expires:
            continue
        result.append((nick, tier.upper(), int(expires)))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Import HORDE donate properties into auth MySQL.")
    parser.add_argument("subscriptions_file", type=Path)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    args = parser.parse_args()

    if args.env.exists():
        load_dotenv(args.env)
    else:
        load_dotenv()

    password = os.getenv("HORDE_AUTH_DB_PASSWORD") or getpass.getpass("MySQL password: ")
    ssl_ca = os.getenv("HORDE_AUTH_DB_SSL_CA")
    if ssl_ca and not Path(ssl_ca).is_absolute():
        ssl_ca = str((Path(__file__).resolve().parent / ssl_ca).resolve())

    conn = pymysql.connect(
        host=os.environ["HORDE_AUTH_DB_HOST"],
        port=int(os.getenv("HORDE_AUTH_DB_PORT", "3306")),
        user=os.environ["HORDE_AUTH_DB_USER"],
        password=password,
        database=os.getenv("HORDE_AUTH_DB_NAME", "defaultdb"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        ssl={"ca": ssl_ca} if ssl_ca else None,
    )
    try:
        props = parse_java_properties(args.subscriptions_file)
        subs = subscriptions_from_properties(props)
        with conn.cursor() as cur:
            for nick, tier, expires_epoch in subs:
                expires_at = datetime.fromtimestamp(expires_epoch, tz=timezone.utc).replace(tzinfo=None)
                cur.execute(
                    """
                    INSERT INTO donate_subscriptions
                        (minecraft_nick, tier, started_at, expires_at, active, source, external_payment_id)
                    VALUES
                        (%s, %s, UTC_TIMESTAMP(), %s, 1, 'horde_donate_properties', %s)
                    ON DUPLICATE KEY UPDATE
                        tier=VALUES(tier),
                        active=1,
                        expires_at=GREATEST(expires_at, VALUES(expires_at))
                    """,
                    (nick, tier, expires_at, f"properties:{nick}:{tier}:{expires_epoch}"),
                )
        conn.commit()
        print(f"imported_subscriptions={len(subs)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
