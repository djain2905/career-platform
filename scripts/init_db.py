"""Create (or re-apply) the Career Platform schema. Runs before every Railway deploy.

Usage:  python -m scripts.init_db
"""
from __future__ import annotations

from app.db import connect, init_schema


def main() -> None:
    with connect() as conn:
        init_schema(conn)
        tables = [
            r["table_name"]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
        ]
        where = f"{conn.info.host}/{conn.info.dbname}"
    print(f"Schema applied to {where}")
    print(f"{len(tables)} tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
